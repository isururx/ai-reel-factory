# AI Reel Factory

An AI-assisted content intelligence and short-form video production platform. M1 establishes Page configuration and strategy foundations; M2 adds multi-Page management.

## Architecture
- Frontend: Next.js App Router + TypeScript
- API: FastAPI + Pydantic
- Database: Supabase-managed PostgreSQL
- ORM and migrations: SQLAlchemy 2.0 + Alembic
- Authentication: Supabase Auth email/password + FastAPI JWT verification through Supabase JWKS
- Object storage: Cloudflare R2 through its S3-compatible API
- Background jobs: Redis + Celery (introduced with asynchronous workflows)
- Production: Piper TTS + FFmpeg + pluggable video-generation worker
- Publishing: Meta Graph API behind server-side approval gates

## Supabase setup
1. Create a Supabase project.
2. In Supabase Project Settings → Database → Connect, select Session Pooler.
3. Copy the connection string into the repository-root .env as DATABASE_URL.
4. Change the URI scheme to postgresql+psycopg:// and retain ?sslmode=require.
5. URL-encode special characters in the database password.
6. Never commit .env or expose database credentials to the browser.

## Supabase Auth setup\n1. In Supabase Dashboard → Authentication → Providers, enable Email authentication.\n2. Configure the allowed site URL as `http://localhost:3000` for local development.\n3. Add `SUPABASE_URL` to the backend `.env`; use the project URL from Project Settings → API.\n4. Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to `frontend/.env.local`. The anon/publishable key is designed for browser use; never put a service-role key in a `NEXT_PUBLIC_` variable.\n5. Backend access tokens are verified against the project JWKS endpoint. Every Page and strategy API request requires a valid bearer token. Page workspaces are scoped to the Supabase user ID.\n6. Existing Pages created before this migration have no owner and will not appear in the authenticated dashboard. Re-create them after signing in, or carefully assign their `owner_id` in the Supabase SQL editor using the authenticated user's UUID.\n\n## Cloudflare R2 setup
1. Create an R2 bucket.
2. Create an R2 API token with Object Read & Write access scoped to that bucket.
3. Add Account ID, Access Key ID, Secret Access Key and bucket name to .env.
4. Keep generated videos private and use short-lived presigned URLs.
5. Never expose R2 credentials through NEXT_PUBLIC variables or commit them to Git.

## Backend quick start
Requirements: Python 3.11+

    cd backend
    python -m venv .venv
    # Windows CMD: .venv\Scripts\activate.bat
    # PowerShell: .venv\Scripts\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    pip install -e '.[dev]'
    python -m alembic upgrade head
    python -m uvicorn app.main:app --reload

Tests use isolated in-memory SQLite and do not require a live Supabase connection.

## Frontend quick start
    cd frontend
    npm install
    npm run dev

Set NEXT_PUBLIC_API_BASE_URL only if your FastAPI API is not at http://127.0.0.1:8000/api/v1. For example:

    NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1

The FastAPI backend allows the configured FRONTEND_ORIGIN (default http://localhost:3000) and http://127.0.0.1:3000 during local development. Copy `frontend/.env.example` to `frontend/.env.local` and fill in the Supabase project URL and anon key.

## Local URLs
- Dashboard: http://localhost:3000
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Page management API
- POST /api/v1/pages — create a Page.
- GET /api/v1/pages and GET /api/v1/pages/{page_id} — list/retrieve Pages.
- PATCH /api/v1/pages/{page_id} — update Page details or active status.
- DELETE /api/v1/pages/{page_id} — delete a Page and its dependent records.
- GET/PUT /api/v1/pages/{page_id}/profile — retrieve or upsert a Page profile.
- POST/GET /api/v1/pages/{page_id}/strategies — create/list strategies.
- PATCH /api/v1/pages/{page_id}/strategies/{strategy_id} — update strategy metadata/status.
- GET/POST /api/v1/pages/{page_id}/strategies/{strategy_id}/versions — list or append strategy versions.

**Security status:** Page and strategy endpoints require Supabase authentication and enforce Page ownership. Keep Supabase service-role keys and database credentials server-side. Meta OAuth credentials and production hardening remain future work.

## Product principles
1. Each Page has isolated profiles, strategies, scripts, analytics and credentials.
2. Human approval is required for scripts and final videos.
3. Editing an approved artifact invalidates its approval.
4. Publishing validates approval against the exact immutable video version.
5. GPU jobs are budget-capped, measurable and shut down when idle.
6. Use original content and properly licensed assets.


## M5 Trend discovery
- Collect RSS 2.0 and Atom feeds using `POST /api/v1/trends/collect` with a list of feed URLs.
- View the account's collected source items with `GET /api/v1/trends`.
- View Page-specific ranked suggestions with `GET /api/v1/pages/{page_id}/trends`.
- Save, dismiss or select a suggestion with `PATCH /api/v1/pages/{page_id}/trends/{recommendation_id}` and a status of `saved`, `dismissed` or `selected`.
- Collection deduplicates source URLs per account and creates separate recommendations using each active Page's niche and audience profile.
- The initial score is a transparent heuristic based on keyword overlap and freshness; it is a triage aid, not a prediction of virality.
- Apply the new schema with `python -m alembic upgrade head` from the backend directory.
- Google Trends, Reddit and YouTube can be connected in later adapters. For now, use their official RSS feeds where available; no scraping or private competitor analytics are used.
