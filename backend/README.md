# PaperRanking Backend

FastAPI + SQLAlchemy (SQLite default) + OpenAlex ingestion + OpenAI classification.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, optionally DATABASE_URL, OPENALEX_MAILTO
```

## Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tables are created on startup. For Alembic migrations instead:

```bash
alembic upgrade head
```

## CLI (from backend/)

```bash
# Preview OpenAlex schema (no DB)
python cli.py preview --journal-code JIS --limit 1

# Ingest all journals
python cli.py ingest --journal-code all --since-year 2010 --max-papers-per-journal 2000

# Load classifications from paper_classifications.json (project root), then classify the rest
python cli.py load-classifications
# Optional: --path /path/to/file.json, --force to overwrite existing

# Classify unclassified papers only
python cli.py classify --limit 300
```

## Endpoints

- `GET /org-rankings` – Organization rankings with category counts
- `GET /debug/summary` – Per-journal and top orgs
- `GET /health` – Health check
