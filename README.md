# AI Reel Factory

An AI-assisted content intelligence and short-form video production platform. M1 establishes Page configuration and strategy foundations; script generation, video production and Meta publishing follow in later milestones.

## Architecture
- Frontend: Next.js App Router + TypeScript
- API: FastAPI + Pydantic
- Database: PostgreSQL (pgvector when semantic retrieval is introduced)
- ORM and migrations: SQLAlchemy 2.0 + Alembic
- Background jobs: Redis + Celery (introduced with asynchronous workflows)
- Production: Piper TTS + FFmpeg + pluggable video-generation worker
- Publishing: Meta Graph API behind server-side approval gates

## Backend quick start
Requirements: Python 3.11+

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Health: http://localhost:8000/health | API docs: http://localhost:8000/docs

## Full stack
1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Apply migrations: `docker compose exec api alembic upgrade head`.
4. Open the frontend at http://localhost:3000.

## API v1
- `POST /api/v1/pages` — create a Page.
- `GET /api/v1/pages` and `GET /api/v1/pages/{page_id}` — list/retrieve Pages.
- `GET/PUT /api/v1/pages/{page_id}/profile` — retrieve or upsert a Page profile.
- `POST/GET /api/v1/pages/{page_id}/strategies` — create/list strategies.
- `GET /api/v1/pages/{page_id}/strategies/{strategy_id}/versions` — list strategy versions.

## Product principles
1. Each Page has isolated profiles, strategies, scripts, analytics and credentials.
2. Human approval is required for scripts and final videos.
3. Editing an approved artifact invalidates its approval.
4. Publishing validates approval against the exact immutable video version.
5. GPU jobs are budget-capped, measurable and shut down when idle.
6. Use original content and properly licensed assets.

**M1 — Data foundation:** SQLAlchemy models, Alembic initial migration, Page/profile/strategy APIs and SQLite-backed API tests. Authentication and production tenant authorization are not enabled yet; these endpoints support the single-owner local MVP.
