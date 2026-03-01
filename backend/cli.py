#!/usr/bin/env python3
"""Typer CLI: preview, ingest, classify."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import typer
from app.db.session import SessionLocal
from app.services.preview import preview_work
from app.services.ingest import ingest_all
from app.services.classify import run_classify, load_classifications_from_json
from app.core.journals import JOURNALS

cli = typer.Typer()


@cli.command()
def preview(
    journal_code: str = typer.Option(..., "--journal-code", "-j", help="Journal code (e.g. JIS)"),
    limit: int = typer.Option(1, "--limit", "-l", help="Number of works to fetch (first one used for schema)"),
):
    """Preview OpenAlex schema: print top-level keys, trimmed JSON, normalized fields, institutions."""
    result = preview_work(journal_code, limit=limit)
    if not result:
        typer.echo(f"Unknown journal code: {journal_code}. Known: {list(JOURNALS.keys())}", err=True)
        raise typer.Exit(1)
    typer.echo("=== Top-level keys ===")
    typer.echo(json.dumps(result.get("top_level_keys", []), indent=2))
    typer.echo("\n=== Trimmed JSON (selected fields) ===")
    typer.echo(json.dumps(result.get("trimmed_json"), indent=2, default=str))
    typer.echo("\n=== Normalized Paper fields we store ===")
    typer.echo(json.dumps(result.get("normalized_paper_fields"), indent=2, default=str))
    typer.echo("\n=== Extracted institutions (unique) ===")
    typer.echo(json.dumps(result.get("institutions", []), indent=2, default=str))


@cli.command()
def ingest(
    journal_code: str = typer.Option("all", "--journal-code", "-j", help="Journal code or 'all'"),
    since_year: int = typer.Option(2010, "--since-year", help="Stop when year < this"),
    max_papers_per_journal: int = typer.Option(2000, "--max-papers-per-journal", help="Max papers per journal"),
):
    """Ingest journals/papers/orgs from OpenAlex into DB (idempotent)."""
    db = SessionLocal()
    try:
        codes = None if journal_code.lower() == "all" else [journal_code]
        result = ingest_all(db, journal_codes=codes, since_year=since_year, max_papers_per_journal=max_papers_per_journal)
        db.commit()
        for code, count in result.items():
            typer.echo(f"  {code}: {count} papers")
    finally:
        db.close()


@cli.command("load-classifications")
def load_classifications(
    path: str = typer.Option(
        None,
        "--path", "-p",
        help="Path to paper_classifications.json (default: project root)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing DB classifications"),
):
    """Load classifications from paper_classifications.json into DB; then run classify for the rest."""
    default_path = Path(__file__).resolve().parent.parent / "paper_classifications.json"
    file_path = Path(path) if path else default_path
    if not file_path.exists():
        typer.echo(f"File not found: {file_path}", err=True)
        raise typer.Exit(1)
    db = SessionLocal()
    try:
        n = load_classifications_from_json(db, file_path, skip_already_classified=not force)
        typer.echo(f"Loaded {n} classifications from {file_path}.")
    finally:
        db.close()


@cli.command()
def classify(
    limit: int = typer.Option(300, "--limit", "-l", help="Max papers to classify"),
    only_unclassified: bool = typer.Option(True, "--only-unclassified/--all", help="Only papers with no category"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-classify even already classified"),
):
    """Classify papers into 5 categories (only unclassified unless --force)."""
    db = SessionLocal()
    try:
        n = run_classify(db, limit=limit, only_unclassified=only_unclassified, force=force)
        typer.echo(f"Classified {n} papers.")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
