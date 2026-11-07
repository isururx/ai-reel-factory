# AI Reel Factory

An AI-assisted content intelligence and short-form video production platform. M1 establishes Page configuration and strategy foundations; script generation, video production and Meta publishing follow in later milestones.

## Architecture
- Frontend: Next.js App Router + TypeScript
- API: FastAPI + Pydantic
- Database: Supabase-managed PostgreSQL
- ORM and migrations: SQLAlchemy 2.0 + Alembic
- Authentication: Supabase Auth (planned; not yet enforced by M1 API routes)
- Vector search: pgvector in Supabase (enable when semantic retrieval is introduced)
- Object storage: Cloudflare R2 through its S3-compatible API
- Background jobs: Redis + Celery (introduced with asynchronous workflows)
- Production: Piper TTS + FFmpeg + pluggable video-generation worker
- Publishing: Meta Graph API behind server-side approval gates

## Supabase setup
1. Create a Supabase project.
2. In Project Settings → Database → Connection string, select the Session Pooler.
3. Copy the connection string into the root .env as DATABASE_URL.
4. Change the URI scheme to postgresql+psycopg:// and retain ?sslmode=require.
5. URL-encode special characters in the database password.
6. Never commit .env or expose the database password to the browser.

Use the Session Pooler for this SQLAlchemy application. It supports the application's connection pooling and is suitable for normal Alembic migration workflows. Avoid the Transaction Pooler for Alembic migrations. Supabase Auth is planned, but M1 remains a single-owner development API until authentication and Page-level authorization are implemented.

## Cloudflare R2 setup
1. Create an R2 bucket, for example ai-reel-factory.
2. Create an R2 API token with Object Read & Write access scoped to that bucket.
3. Add the Account ID, Access Key ID, Secret Access Key and bucket name to .env.
4. Keep generated videos private by default and issue short-lived presigned URLs for previews.
5. Store only the R2 object key and asset metadata in PostgreSQL.

The S3-compatible endpoint is https://<ACCOUNT_ID>.r2.cloudflarestorage.com. Never expose R2 credentials through NEXT_PUBLIC variables or commit them to Git.

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

For local development, settings load backend/.env or the repository-root .env. Copy .env.example to the repository root and configure Supabase and R2. Tests use isolated in-memory SQLite and do not require a live Supabase connection.

Health: http://localhost:8000/health | API docs: http://localhost:8000/docs

## Full stack
1. Copy .env.example to .env and configure Supabase and R2.
2. Run docker compose up --build.
3. Apply migrations: docker compose exec api python -m alembic upgrade head.
4. Open the frontend at http://localhost:3000.

Docker Compose runs Redis locally; PostgreSQL is managed by Supabase.

## API v1
- POST /api/v1/pages — create a Page.
- GET /api/v1/pages and GET /api/v1/pages/{page_id} — list/retrieve Pages.
- GET/PUT /api/v1/pages/{page_id}/profile — retrieve or upsert a Page profile.
- POST/GET /api/v1/pages/{page_id}/strategies — create/list strategies.
- GET /api/v1/pages/{page_id}/strategies/{strategy_id}/versions — list strategy versions.

## Product principles
1. Each Page has isolated profiles, strategies, scripts, analytics and credentials.
2. Human approval is required for scripts and final videos.
3. Editing an approved artifact invalidates its approval.
4. Publishing validates approval against the exact immutable video version.
5. GPU jobs are budget-capped, measurable and shut down when idle.
6. Use original content and properly licensed assets.

M1: SQLAlchemy models, Alembic initial migration, Page/profile/strategy APIs and SQLite-backed API tests. Supabase connectivity is configured through DATABASE_URL; Supabase Auth and production tenant authorization are not enabled yet.
