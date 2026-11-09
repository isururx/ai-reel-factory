# Reference Intelligence — Direct Video Analysis Queue

Reference Intelligence now uses a direct video-submission workflow. The old Reference Page → collected posts → video library navigation is no longer required for new analyses.

## User workflow

1. Open **Reference Intelligence**.
2. Select one of the user's Page workspaces.
3. Paste a public Facebook video/Reel URL.
4. Optionally enter views, reactions, shares, comment count, comment samples, and notes.
5. Submit. The API saves a durable queue job and returns HTTP 202.
6. A single Celery worker processes jobs in FIFO order: download at up to 720p → upload privately to R2 → analyze with Gemini → save video, metrics, analysis and Page-scoped creative insight.
7. The UI polls the queue and displays completed videos with the exact analysis completion date/time.

## Queue architecture

- PostgreSQL table: `reference_video_jobs` is the durable source of truth.
- Redis is the Celery broker.
- One worker process with concurrency 1 handles one job at a time.
- Each worker invocation claims the oldest `queued` row ordered by `created_at ASC, id ASC` under a row lock.
- A task schedules another drain after consuming a job.
- Queue position is calculated from earlier queued rows; it is not a fixed value.
- Job states: `queued`, `processing`, `completed`, `failed`.
- A failure is recorded on the job with an error message. It does not silently disappear.

The strict FIFO guarantee depends on running only one worker process with concurrency 1. Do not scale this worker horizontally unless the queue-claiming and ordering policy is deliberately changed.

## API

- `POST /api/v1/pages/{page_id}/reference-videos/queue` — submit URL and manual context; returns 202.
- `GET /api/v1/pages/{page_id}/reference-videos/queue` — queue status and positions.
- `GET /api/v1/pages/{page_id}/reference-videos` — completed analyses for the selected Page.
- `POST /api/v1/pages/{page_id}/reference-videos/queue/{job_id}/upload` — attach a user-provided video to a `needs_upload` job and resume processing.
- `GET /api/v1/pages/{page_id}/reference-videos/{video_id}/file` — short-lived signed R2 URL.

Example submission:

```json
{
  "source_url": "https://www.facebook.com/reel/123456",
  "title": "Optional title",
  "views_count": 12000,
  "reactions_count": 850,
  "shares_count": 40,
  "comments_count": 70,
  "manual_comments": ["Great explanation", "Part two please"],
  "engagement_notes": "Observed manually on 9 Nov."
}
```

Blank metrics are represented as null, not zero. Metrics and comment samples remain labelled as user-provided context.

## Local setup (Windows CMD)

Start Redis first. Then install updated backend dependencies:

```cmd
cd /d "D:\Vid Projects (AI)\ai-reel-factory\backend"
.venv\Scripts\activate
python -m pip install -e .
python -m alembic upgrade head
```

Run the API in one terminal:

```cmd
uvicorn app.main:app --reload
```

Run the FIFO worker in a second terminal (Windows uses the solo pool):

```cmd
celery -A app.worker:celery_app worker --loglevel=INFO --pool=solo --concurrency=1 --prefetch-multiplier=1
```

Redis must be reachable at the configured `REDIS_URL` (default `redis://localhost:6379/0`). The worker also needs the existing Gemini and Cloudflare R2 environment variables.

## Data model

- `reference_video_jobs`: durable submission, manual metrics, queue state, timestamps and failure detail.
- `reference_videos`: final downloaded asset, R2 key, metrics, analysis JSON and `analyzed_at`.
- `reference_creative_insights`: Page-scoped analysis ready for human review.

Existing reference videos are backfilled to their Page workspace by migration 0008.

## Operational notes

- Automatic downloads are limited to public videos accessible without signing in; no cookies, login sessions or access-control bypass. When a URL requires login, users can upload a video file they are authorized to use (MP4, WebM, MOV or MKV, maximum 300 MB). The uploaded file follows the same R2 → Gemini analysis pipeline.
- Downloads remain capped by the downloader's 720p preference, 15-minute duration and 300 MB limit.
- Analysis is performed in the worker, not inside the HTTP request.
- The worker is deliberately single-consumer for FIFO ordering.
- For production, run Redis and the worker as managed services and add monitoring/recovery for jobs left in `processing` after an unexpected machine failure.
