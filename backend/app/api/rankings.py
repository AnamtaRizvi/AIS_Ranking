"""GET /org-rankings."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Paper, PaperOrg, Organization, Category, Journal

router = APIRouter(prefix="/org-rankings", tags=["rankings"])

TOP_N = 50


@router.get("", response_model=List[Dict[str, Any]])
def get_org_rankings(
    db: Session = Depends(get_db),
    journal_code: Optional[str] = Query(None, description="Filter counts by journal; omit for all journals"),
):
    """
    Return top 50 organizations with paper counts per category and total, sorted by total desc.
    If journal_code is set, counts are restricted to papers in that journal only.
    """
    cats = db.query(Category).all()
    cat_names = {c.id: c.name for c in cats}

    base = select(
        Organization.id,
        Organization.name,
        Organization.country_code,
        func.count(PaperOrg.paper_id).label("total"),
    ).join(PaperOrg, Organization.id == PaperOrg.org_id)
    if journal_code:
        base = (
            base.join(Paper, PaperOrg.paper_id == Paper.id)
            .join(Journal, Paper.journal_id == Journal.id)
            .where(Journal.code == journal_code)
        )
    org_totals = (
        db.execute(
            base.group_by(Organization.id, Organization.name, Organization.country_code)
            .order_by(func.count(PaperOrg.paper_id).desc())
            .limit(TOP_N)
        )
        .all()
    )

    out = []
    for org_id, org_name, country_code, total in org_totals:
        counts = {name: 0 for name in cat_names.values()}
        cat_query = (
            select(Category.name, func.count(Paper.id).label("cnt"))
            .select_from(PaperOrg)
            .join(Paper, PaperOrg.paper_id == Paper.id)
            .join(Category, Paper.best_category_id == Category.id)
            .where(PaperOrg.org_id == org_id, Paper.best_category_id.isnot(None))
        )
        if journal_code:
            cat_query = cat_query.join(Journal, Paper.journal_id == Journal.id).where(Journal.code == journal_code)
        rows = db.execute(cat_query.group_by(Category.name)).all()
        for cname, cnt in rows:
            if cname in counts:
                counts[cname] = cnt
        out.append({
            "organization": org_name,
            "country_code": country_code or "",
            "counts": counts,
            "total": total,
        })
    return out
