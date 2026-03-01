"""Classify papers into 5 categories (only unclassified unless --force)."""
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.journals import PAPER_CATEGORIES
from app.db.models import Paper, Category, PaperCategory, PaperOrg


def _openalex_work_id_from_url(paper_id: str) -> Optional[str]:
    """Extract OpenAlex work ID from URL like https://openalex.org/W4408414291."""
    if not paper_id:
        return None
    s = (paper_id or "").strip()
    if "/" in s:
        s = s.rstrip("/").rsplit("/", 1)[-1]
    return s if s.startswith("W") and s[1:].isdigit() else None


KEYWORDS_BY_CATEGORY = {
    "Accounting & Financial AI": ["accounting", "audit", "finance", "financial", "ledger", "tax"],
    "Business Intelligence & Decision Support": ["business intelligence", "dashboard", "decision support", "BI", "MIS", "KPI"],
    "Information Systems & Applied Analytics": ["information system", "ERP", "governance", "adoption", "analytics", "IS "],
    "Engineering & Industrial AI": ["manufacturing", "supply chain", "operations", "industrial", "production"],
    "Core AI & Data Science Methods": ["algorithm", "machine learning", "neural", "model", "classification", "deep learning"],
}


def _keyword_scores(paper: Paper) -> Dict[str, float]:
    text = ((paper.title or "") + " " + (paper.abstract_text or "") + " " + (paper.concepts_hint or "")).lower()
    scores = {}
    for cat, keywords in KEYWORDS_BY_CATEGORY.items():
        s = sum(1 for k in keywords if k in text)
        scores[cat] = min(1.0, s * 0.25)
    return scores


def _classify_batch_openai(papers: List[Paper], model: str) -> List[Dict[str, Any]]:
    client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    if not client:
        return []
    prompt = """Classify each paper into exactly ONE label from:
["Accounting & Financial AI","Business Intelligence & Decision Support","Information Systems & Applied Analytics","Engineering & Industrial AI","Core AI & Data Science Methods"]
Use the OpenAlex topic context strongly.
- Accounting/auditing/finance + ML/AI → Accounting & Financial AI
- Dashboards/decision support/BI/MIS for org decisions → Business Intelligence & Decision Support
- IS adoption, ERP, governance, analytics in org settings → Information Systems & Applied Analytics
- Manufacturing/operations/supply chain/industrial + AI → Engineering & Industrial AI
- Mostly algorithms/models/methods, little domain focus → Core AI & Data Science Methods

Return a JSON array with one object per paper in order: [{"label":"...", "confidence":0.0-1.0, "why":"<=12 words"}, ...]

Papers:
"""
    for i, p in enumerate(papers, 1):
        prompt += f"\n{i}. Title: {p.title}\nAbstract: {p.abstract_text or ''}\nOpenAlexHint: {p.concepts_hint or ''}\n---"
    prompt += "\n\nJSON array only:"
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return only a valid JSON array. Each element: {\"label\": \"...\", \"confidence\": number, \"why\": \"...\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        text = r.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        data = json.loads(text)
        if isinstance(data, dict):
            for key in ("classifications", "results", "papers", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
            return []
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _parse_batch_response(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for item in raw:
        label = item.get("label") or ""
        if label not in PAPER_CATEGORIES:
            label = "Core AI & Data Science Methods"
        out.append({
            "label": label,
            "confidence": float(item.get("confidence", 0.5)),
            "why": (item.get("why") or "")[:200],
        })
    return out


def get_unclassified_papers(
    db: Session,
    limit: int = 300,
    only_from_top_orgs: bool = True,
    top_n_orgs: int = 50,
) -> List[Paper]:
    """
    Unique papers with no best_category_id.
    If only_from_top_orgs, restrict to papers that have at least one author from a top-N org.
    Each paper is returned at most once (no duplicate classification for same paper across orgs).
    """
    from sqlalchemy import func
    q = select(Paper).where(Paper.best_category_id.is_(None))
    if only_from_top_orgs:
        top_org_rows = db.execute(
            select(PaperOrg.org_id, func.count(PaperOrg.paper_id).label("c"))
            .group_by(PaperOrg.org_id)
            .order_by(func.count(PaperOrg.paper_id).desc())
            .limit(top_n_orgs)
        ).all()
        top_org_ids = [r[0] for r in top_org_rows]
        if top_org_ids:
            # Distinct paper IDs that appear in any of the top orgs (same paper counted once)
            paper_ids_sub = select(PaperOrg.paper_id).where(PaperOrg.org_id.in_(top_org_ids)).distinct()
            q = q.where(Paper.id.in_(paper_ids_sub))
    q = q.distinct().limit(limit)
    # .scalars() so we get Paper ORM objects, not Row; each paper appears once
    return list(db.execute(q).scalars().all())


def load_classifications_from_json(
    db: Session,
    path: Path,
    skip_already_classified: bool = True,
) -> int:
    """
    Load classifications from paper_classifications.json into the DB.
    JSON must have a "classifications" array with items: paper_id (OpenAlex URL),
    category (name), confidence, reasoning (stored as why).
    Returns number of papers updated. Skips papers not in DB or unknown category.
    """
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    classifications = data.get("classifications") or []
    if not classifications:
        return 0
    categories = {c.name: c for c in db.execute(select(Category)).scalars().all()}
    for name in PAPER_CATEGORIES:
        if name not in categories:
            c = Category(name=name)
            db.add(c)
            db.flush()
            categories[name] = c
    updated = 0
    for item in classifications:
        paper_id_url = item.get("paper_id") or ""
        work_id = _openalex_work_id_from_url(paper_id_url)
        if not work_id:
            continue
        category_name = (item.get("category") or "").strip()
        if category_name not in PAPER_CATEGORIES:
            category_name = "Core AI & Data Science Methods"
        cat = categories.get(category_name)
        if not cat:
            continue
        row = db.execute(select(Paper).where(Paper.openalex_work_id == work_id)).scalar_one_or_none()
        if not row and paper_id_url:
            row = db.execute(select(Paper).where(Paper.openalex_work_id == paper_id_url.strip())).scalar_one_or_none()
        if not row:
            continue
        paper = row
        if skip_already_classified and paper.best_category_id is not None:
            continue
        confidence = item.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None
        why = (item.get("reasoning") or item.get("why") or "")[:500]
        existing = db.execute(
            select(PaperCategory).where(
                PaperCategory.paper_id == paper.id,
                PaperCategory.category_id == cat.id,
            )
        ).scalar_one_or_none()
        if existing:
            existing.score = 1.0
            existing.confidence = confidence
            existing.why = why or existing.why
            existing.model = "import"
        else:
            db.add(PaperCategory(
                paper_id=paper.id,
                category_id=cat.id,
                score=1.0,
                confidence=confidence,
                why=why,
                model="import",
            ))
        paper.best_category_id = cat.id
        updated += 1
    if updated:
        db.commit()
    return updated


def run_classify(
    db: Session,
    limit: int = 300,
    only_unclassified: bool = True,
    force: bool = False,
    batch_size: int = 30,
    keyword_margin: float = 0.5,
) -> int:
    """
    Classify papers into one category each. Each paper is classified at most once
    (by paper id); the same paper may be linked to multiple orgs (PaperOrg), and
    org-level counts in /org-rankings are computed from Paper.best_category_id,
    so one paper's category correctly contributes to each org that authored it.
    If only_unclassified, only papers with no best_category. If force, re-classify.
    Returns number classified.
    """
    if force:
        papers = list(db.execute(select(Paper).limit(limit)).scalars().all())
    else:
        papers = get_unclassified_papers(db, limit=limit)
    if not papers:
        return 0
    categories = db.query(Category).all()
    cat_map = {c.name: c.id for c in categories}
    if len(cat_map) < 5:
        for name in PAPER_CATEGORIES:
            if name not in cat_map:
                c = Category(name=name)
                db.add(c)
                db.flush()
                cat_map[name] = c.id
    classified = 0
    model = settings.OPENAI_MODEL
    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        results = []
        for p in batch:
            scores = _keyword_scores(p)
            best_cat = max(scores, key=scores.get)
            best_score = scores[best_cat]
            if best_score >= keyword_margin and best_score > 0:
                results.append({"label": best_cat, "confidence": best_score, "why": "keyword match"})
            else:
                results.append(None)
        need_openai = [batch[j] for j in range(len(batch)) if results[j] is None]
        if need_openai and settings.OPENAI_API_KEY:
            openai_results = _classify_batch_openai(need_openai, model)
            parsed = _parse_batch_response(openai_results)
            idx = 0
            for j in range(len(batch)):
                if results[j] is None:
                    if idx < len(parsed):
                        results[j] = parsed[idx]
                        idx += 1
                    else:
                        results[j] = {"label": "Core AI & Data Science Methods", "confidence": 0.5, "why": "fallback"}
        for p, res in zip(batch, results):
            if not res:
                continue
            cat_id = cat_map.get(res["label"])
            if not cat_id:
                continue
            existing = db.execute(
                select(PaperCategory).where(PaperCategory.paper_id == p.id, PaperCategory.category_id == cat_id)
            ).scalar_one_or_none()
            if existing:
                existing.score = 1.0
                existing.confidence = res.get("confidence")
                existing.why = res.get("why")
                existing.model = model
            else:
                db.add(PaperCategory(
                    paper_id=p.id,
                    category_id=cat_id,
                    score=1.0,
                    confidence=res.get("confidence"),
                    why=res.get("why"),
                    model=model,
                ))
            p.best_category_id = cat_id
            classified += 1
        db.commit()
        if need_openai:
            time.sleep(1)
    return classified
