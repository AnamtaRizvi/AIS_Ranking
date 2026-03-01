"""Ingest journals, papers, orgs from OpenAlex into DB (idempotent)."""
from typing import Any, Dict, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openalex import (
    get_source_by_issn,
    search_source_by_name,
    iter_works_by_source,
    abstract_inverted_index_to_text,
    concepts_to_hint_string,
)
from app.core.journals import JOURNALS
from app.db.models import Journal, Paper, Organization, PaperOrg
from app.services.preview import extract_institutions_from_work, normalize_work_to_paper_fields


def _get_or_create_journal(db: Session, code: str) -> Journal:
    row = db.execute(select(Journal).where(Journal.code == code)).scalar_one_or_none()
    if row:
        return row
    conf = JOURNALS[code]
    j = Journal(
        code=code,
        name=conf["name"],
        issn_online=conf.get("issn_online"),
    )
    db.add(j)
    db.flush()
    return j


def _resolve_source_id(code: str) -> Optional[str]:
    conf = JOURNALS[code]
    source = get_source_by_issn(conf["issn_online"]) if conf.get("issn_online") else None
    if not source:
        source = search_source_by_name(conf["name"])
    if not source:
        return None
    return (source.get("id") or "").split("/")[-1]


def _upsert_paper(
    db: Session,
    journal_id: int,
    work: Dict[str, Any],
) -> Paper:
    oid = work.get("id") or ""
    row = db.execute(select(Paper).where(Paper.openalex_work_id == oid)).scalar_one_or_none()
    fields = normalize_work_to_paper_fields(work)
    if row:
        row.title = fields["title"]
        row.year = fields["year"]
        row.doi = fields["doi"]
        row.published_date = fields["published_date"]
        row.primary_url = fields["primary_url"]
        row.abstract_text = fields["abstract_text"]
        row.concepts_hint = fields["concepts_hint"]
        row.raw_json = work
        db.flush()
        return row
    p = Paper(
        openalex_work_id=oid,
        journal_id=journal_id,
        raw_json=work,
        **{k: v for k, v in fields.items() if k != "openalex_work_id"},
    )
    db.add(p)
    db.flush()
    return p


def _upsert_org(db: Session, openalex_org_id: Optional[str], name: str, country_code: Optional[str]) -> Organization:
    if openalex_org_id:
        row = db.execute(select(Organization).where(Organization.openalex_org_id == openalex_org_id)).scalar_one_or_none()
        if row:
            return row
    o = Organization(openalex_org_id=openalex_org_id, name=name, country_code=country_code)
    db.add(o)
    db.flush()
    return o


def ingest_journal(
    db: Session,
    code: str,
    since_year: int = 2010,
    max_papers: int = 2000,
) -> int:
    """Ingest one journal. Returns count of papers processed (new + updated)."""
    source_id = _resolve_source_id(code)
    if not source_id:
        return 0
    journal = _get_or_create_journal(db, code)
    if not journal.openalex_source_id:
        journal.openalex_source_id = source_id
        db.flush()
    count = 0
    for work in iter_works_by_source(source_id, per_page=200):
        year = work.get("publication_year")
        if year is not None and year < since_year:
            break
        if count >= max_papers:
            break
        paper = _upsert_paper(db, journal.id, work)
        count += 1
        insts = extract_institutions_from_work(work)
        for i in insts:
            org = _upsert_org(db, i["openalex_org_id"], i["name"], i.get("country_code"))
            link = db.execute(
                select(PaperOrg).where(PaperOrg.paper_id == paper.id, PaperOrg.org_id == org.id)
            ).scalar_one_or_none()
            if not link:
                db.add(PaperOrg(paper_id=paper.id, org_id=org.id))
        db.flush()
    return count


def ingest_all(
    db: Session,
    journal_codes: Optional[list] = None,
    since_year: int = 2010,
    max_papers_per_journal: int = 2000,
) -> Dict[str, int]:
    """Ingest journals. journal_codes=None or ['all'] means all. Returns {code: count}."""
    codes = journal_codes or list(JOURNALS.keys())
    if len(codes) == 1 and (codes[0] or "").upper() == "ALL":
        codes = list(JOURNALS.keys())
    result = {}
    for code in codes:
        if code in JOURNALS:
            result[code] = ingest_journal(db, code, since_year, max_papers_per_journal)
    return result
