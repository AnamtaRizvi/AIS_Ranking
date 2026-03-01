"""GET /debug/summary."""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Journal, Paper, PaperOrg, Organization

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/summary", response_model=Dict[str, Any])
def get_debug_summary(db: Session = Depends(get_db)):
    """
    Return per_journal (code, name, paper_count) and top_orgs_overall (organization, total).
    """
    per_journal = []
    for row in db.execute(select(Journal)).scalars().all():
        j = row[0]
        cnt = db.execute(select(func.count(Paper.id)).where(Paper.journal_id == j.id)).scalar() or 0
        per_journal.append({"code": j.code, "name": j.name, "paper_count": cnt})
    top_orgs = db.execute(
        select(Organization.name, func.count(PaperOrg.paper_id).label("total"))
        .join(PaperOrg, Organization.id == PaperOrg.org_id)
        .group_by(Organization.id, Organization.name)
        .order_by(func.count(PaperOrg.paper_id).desc())
        .limit(20)
    ).all()
    top_orgs_overall = [{"organization": name, "total": total} for name, total in top_orgs]
    return {
        "per_journal": per_journal,
        "top_orgs_overall": top_orgs_overall,
    }
