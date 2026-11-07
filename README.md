# AI Reel Factory

An AI-assisted content intelligence and short-form video production platform. The first milestone focuses on a single-page local MVP: page profile, strategy, script generation, and human script approval. Video generation and Meta publishing are intentionally deferred until the core workflow is reliable.

## Architecture

- **Frontend:** Next.js App Router + TypeScript
- **API:** FastAPI + Pydantic
- **Database:** PostgreSQL (pgvector will be enabled when semantic retrieval is introduced)
- **Background jobs:** Redis + Celery (added when asynchronous workflows are introduced)
- **Production:** Piper TTS + FFmpeg + pluggable video-generation worker
- **Publishing:** Meta Graph API integration, behind server-side approval gates

## Repository layout

```text
backend/       FastAPI application and tests
frontend/      Next.js dashboard
infrastructure Docker Compose and local infrastructure config
docs/          Architecture decisions and implementation notes
scripts/       Developer utilities
```

## Quick start (backend)

Requirements: Python 3.11+

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

API health check: http://localhost:8000/health  
Interactive API docs: http://localhost:8000/docs

## Quick start (full stack)

1. Copy `.env.example` to `.env` and update local values.
2. Run `docker compose up --build`.
3. Backend: http://localhost:8000; frontend: http://localhost:3000.

The initial frontend is a placeholder until the first dashboard milestone is implemented.

## Product principles

1. One Page first; design the data model for multiple Pages.
2. Each Page has isolated profiles, strategies, scripts, analytics, and credentials.
3. Human approval is required for scripts and final videos.
4. Editing an approved artifact invalidates its approval.
5. Publishing must validate approval server-side against the exact immutable video version.
6. GPU jobs are budget-capped, measurable, and shut down when idle.
7. Prefer original content and properly licensed assets; do not copy other creators' videos.

## Current milestone

**M0 — Project foundation:** repository scaffold, local API, frontend shell, and Docker-based PostgreSQL/Redis services.

Next: implement database models and migrations for Pages, page profiles, strategies, scripts, script versions, and approval events.
