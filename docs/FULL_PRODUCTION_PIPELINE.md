# AI Reel Factory — Full Production Pipeline Development Note

## Confirmed product decisions
- One Page strategy per script-generation batch.
- Pattern and hook selection supports manual selection and automatic selection.
- Manual Script Studio mode retrieves relevant patterns from the selected Page and lets the user adjust them.
- Quantity supports an explicit count or filling remaining daily publishing capacity.
- Every script requires human approval before video generation.
- Once a video is rendered successfully, it proceeds automatically to scheduling and Facebook publishing.
- Facebook is the initial publishing destination.
- Scheduling supports both Page-configured posting slots and later performance-based optimisation.
- LTX-2.5 on Vast.ai is the candidate video engine; its deployed endpoint/workflow is not yet known.

## End-to-end workflow
1. Select a Facebook Page and exactly one active strategy/version.
2. Choose automatic generation or manual brief generation.
3. Select patterns/hooks manually, request automatic selection, or combine both.
4. Create a durable script batch and generate scripts asynchronously through Celery.
5. Review/edit each script in Script Studio. Approval applies to one immutable ScriptVersion.
6. Approval creates one idempotent video-production job for that exact version.
7. A provider adapter submits the request to the configured LTX/Vast.ai workflow, tracks status and stores the result in Cloudflare R2.
8. A scheduler assigns the next valid Page-specific slot using timezone, posting slots, daily cap and minimum spacing.
9. A separate Facebook publishing worker publishes the Reel and records Meta IDs/results.
10. Performance data can later optimise slots, but never overrides the Page's configured safety limits.

## Architecture and invariants
- PostgreSQL is the durable source of truth; Redis/Celery transports work.
- Script generation, video production, scheduling and publishing are separate tasks/queues.
- Every batch, pattern lookup, strategy and job is constrained by both owner_id and page_id.
- Store snapshots of strategy version, selected pattern IDs and prompt inputs with each batch/script.
- A rejected or unapproved script cannot create a video job.
- Unique constraints and transactional state transitions prevent duplicate video jobs and publications.
- Meta failures do not re-run video generation.
- Provider-specific details live behind an adapter. Do not assume a live Vast.ai endpoint exists.

## Initial implementation slice
This branch starts the durable data foundation: batch records, video production jobs, Page publishing settings, scheduled publication records and an Alembic migration. Next slices add API validation and Celery workers, then the provider adapter, scheduling logic, Facebook publishing, UI and tests.

## Required deployment configuration before live production
- Vast.ai instance/API endpoint, workflow contract, authentication and callback/polling mechanism.
- LTX-2.5 workflow definition, including image/audio inputs and output artifact format.
- Cloudflare R2 credentials and bucket.
- Facebook Page access token, Page ID and required publishing permissions.
- Redis URL and Celery worker deployment.
- Per-Page timezone, daily Reel cap, posting slots and minimum spacing.
