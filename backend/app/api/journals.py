"""GET /journals — list journals with paper count and category breakdown."""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Journal, Paper, Category

router = APIRouter(tags=["journals"])


@router.get("/journals", response_model=List[Dict[str, Any]])
def get_journals(db: Session = Depends(get_db)):
    """
    Return list of journals with paper_count and counts per category for each.
    """
    cat_objs = db.execute(select(Category)).scalars().all()
    cat_names = {c.id: c.name for c in cat_objs}
    out = []
    for j in db.execute(select(Journal)).scalars().all():
        total = db.execute(
            select(func.count(Paper.id)).where(Paper.journal_id == j.id)
        ).scalar() or 0
        counts = {name: 0 for name in cat_names.values()}
        breakdown = db.execute(
            select(Category.name, func.count(Paper.id).label("cnt"))
            .select_from(Paper)
            .join(Category, Paper.best_category_id == Category.id)
            .where(Paper.journal_id == j.id, Paper.best_category_id.isnot(None))
            .group_by(Category.name)
        ).all()
        for cname, cnt in breakdown:
            if cname in counts:
                counts[cname] = cnt
        out.append({
            "code": j.code,
            "name": j.name,
            "paper_count": total,
            "counts": counts,
        })
    return out
