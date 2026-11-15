# Video generation engine

## Current implementation

The video pipeline starts only after the owner approves the latest immutable ScriptVersion. The approval endpoint creates one VideoProductionJob per version (enforced by the existing unique constraint), stores a snapshot of the exact approved content, and dispatches a Celery task. Repeated approval requests reuse the existing job rather than creating another one.

The initial adapter is MockVideoProvider, selected by VIDEO_PROVIDER=mock (the default). It exercises the queue, provider interface, state transitions and job API without renting a GPU. A mock job reports completed to demonstrate a successful provider lifecycle, but its metadata explicitly says that no MP4 was created or uploaded. Its mock:// output reference is not a playable video and must never be treated as a production asset.

List jobs for a Page with GET /api/v1/pages/{page_id}/video-jobs.

## Next adapter: LTX-2.5 on Vast.ai

The provider contract is isolated in app/services/video_generation/base.py. A real adapter must submit a render request, persist the remote provider job ID, poll or receive completion, download the resulting MP4, validate it, upload it to Cloudflare R2, and only then mark the job completed. It must also support cancellation/timeouts and safe retries without submitting duplicate renders. Do not set VIDEO_PROVIDER to an unsupported provider name until that adapter is implemented.
