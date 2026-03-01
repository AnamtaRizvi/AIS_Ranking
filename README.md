# PaperRanking

Backend: FastAPI + SQLite/Postgres + OpenAlex ingestion + OpenAI classification.  
Frontend: Next.js (rankings and debug tables only).  
UI changes never require re-fetching OpenAlex or re-calling OpenAI.

## Project structure

```
PaperRanking/
  backend/          # FastAPI, DB, ingest, classify, read APIs
  frontend/         # Next.js, tables only
  backend/legacy/   # Old static HTML script (optional)
```

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and optionally DATABASE_URL, OPENALEX_MAILTO
```

Create DB (SQLite by default):

```bash
cd backend
alembic upgrade head
# Or: tables are created on first API run via main.py lifespan
```

Run API:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Commands (run from `backend/` with venv active)

Preview OpenAlex schema (no DB):

```bash
python cli.py preview --journal-code JIS --limit 1
```

Ingest journals/papers/orgs (idempotent):

```bash
python cli.py ingest --journal-code all --since-year 2010 --max-papers-per-journal 2000
```

Load existing classifications from `paper_classifications.json` (project root), then classify the rest:

```bash
python cli.py load-classifications
# Custom path:
python cli.py load-classifications --path /path/to/paper_classifications.json
# Overwrite already classified in DB:
python cli.py load-classifications --force
```

Classify papers (only unclassified by default):

```bash
python cli.py classify --limit 300
# Classify all papers (including already classified):
python cli.py classify --limit 100 --all
# Re-classify and overwrite:
python cli.py classify --limit 100 --force
```

## Frontend

```bash
cd frontend
npm install
# Optional: set NEXT_PUBLIC_API_URL=http://localhost:8000 (default)
npm run dev
```

### Deploy env vars

- Vercel (`frontend`): `NEXT_PUBLIC_API_URL=https://ais-ranking.onrender.com`
- Render (`backend`): `CORS_ORIGINS=https://<your-vercel-domain>,http://localhost:3000`

- **/** – Organization rankings table (counts per category + total).
- **/debug** – Journal counts + top orgs overall.

Frontend only calls read APIs; it never triggers ingest or classify.

## API endpoints

- `GET /org-rankings` – List of orgs with `organization`, `country_code`, `counts` (per category), `total`.
- `GET /debug/summary` – `per_journal`, `top_orgs_overall`.
- `GET /health` – Health check.

## Optional: Postgres

```bash
cd backend
docker-compose up -d
# In .env: DATABASE_URL=postgresql://user:pass@localhost:5432/paperranking
alembic upgrade head
```

## Legacy

The old script that fetched OpenAlex, called OpenAI, and wrote static HTML is in `backend/legacy/fetch_papers.py`. It is no longer used by the app.
