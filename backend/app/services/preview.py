"""OpenAlex schema preview and field mapping (no DB)."""
import json
from typing import Any, Dict, List, Optional

from app.clients.openalex import (
    get_source_by_issn,
    search_source_by_name,
    iter_works_by_source,
    abstract_inverted_index_to_text,
    concepts_to_hint_string,
)
from app.core.journals import JOURNALS


def normalize_work_to_paper_fields(work: Dict[str, Any]) -> Dict[str, Any]:
    """Map OpenAlex work JSON to our Paper fields (no raw_json)."""
    oid = work.get("id") or ""
    title = work.get("title") or "No title"
    year = work.get("publication_year")
    doi = work.get("doi")
    if doi and doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    published_date = work.get("publication_date")
    primary_url = None
    pl = work.get("primary_location") or {}
    if isinstance(pl, dict):
        primary_url = pl.get("landing_page_url") or work.get("id")
    else:
        primary_url = work.get("id")
    abstract_text = abstract_inverted_index_to_text(work.get("abstract_inverted_index"))
    concepts_hint = concepts_to_hint_string(work.get("concepts"))
    return {
        "openalex_work_id": oid,
        "title": title,
        "year": year,
        "doi": doi,
        "published_date": published_date,
        "primary_url": primary_url,
        "abstract_text": abstract_text[:2000] if abstract_text else None,
        "concepts_hint": concepts_hint[:2000] if concepts_hint else None,
    }


def extract_institutions_from_work(work: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unique institutions from authorships[].institutions[]."""
    seen = set()
    out = []
    for authorship in work.get("authorships") or []:
        for inst in authorship.get("institutions") or []:
            if not inst or not inst.get("id"):
                continue
            iid = inst["id"]
            if iid in seen:
                continue
            seen.add(iid)
            out.append({
                "openalex_org_id": iid,
                "name": inst.get("display_name") or "Unknown",
                "country_code": inst.get("country_code"),
            })
    return out


def preview_work(
    journal_code: str,
    limit: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Resolve journal, fetch up to `limit` works, return preview dict with:
    - top_level_keys
    - trimmed_json (selected keys)
    - normalized_paper_fields
    - institutions
    """
    if journal_code.upper() == "ALL" or journal_code not in JOURNALS:
        return None
    conf = JOURNALS[journal_code]
    issn = conf.get("issn_online")
    source = None
    if issn:
        source = get_source_by_issn(issn)
    if not source:
        source = search_source_by_name(conf["name"])
    if not source:
        return None
    source_id = (source.get("id") or "").split("/")[-1]
    works = []
    for w in iter_works_by_source(source_id, per_page=min(200, max(1, limit))):
        works.append(w)
        if len(works) >= limit:
            break
    if not works:
        return {
            "journal_code": journal_code,
            "source_id": source_id,
            "source_display_name": source.get("display_name"),
            "message": "No works found",
            "top_level_keys": [],
            "trimmed_json": None,
            "normalized_paper_fields": None,
            "institutions": [],
        }
    work = works[0]
    top_level_keys = list(work.keys())
    trimmed = {
        "id": work.get("id"),
        "title": work.get("title"),
        "doi": work.get("doi"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "primary_location": work.get("primary_location"),
        "authorships": [
            {"institutions": a.get("institutions")}
            for a in (work.get("authorships") or [])[:3]
        ],
        "concepts": (work.get("concepts") or [])[:5],
        "abstract_inverted_index": (
            dict(list((work.get("abstract_inverted_index") or {}).items())[:5])
        ),
    }
    return {
        "journal_code": journal_code,
        "source_id": source_id,
        "source_display_name": source.get("display_name"),
        "top_level_keys": top_level_keys,
        "trimmed_json": trimmed,
        "normalized_paper_fields": normalize_work_to_paper_fields(work),
        "institutions": extract_institutions_from_work(work),
    }
