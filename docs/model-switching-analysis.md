# Video Analysis Model Switching

## Model order

The reference-video analysis pipeline uses Google Gemini only:
1. Primary: `gemini-3.5-flash-lite`
2. Fallback: `gemini-2.5-flash`

There are no NVIDIA NIM, Nemotron, Qwen, or other model integrations in this pipeline.

## Behavior

- The primary model is attempted first.
- On API errors, missing credentials, timeouts, malformed JSON, or invalid analysis output, switch immediately to Gemini 2.5 Flash.
- No retry/backoff occurs between models.
- The first valid structured response wins and is passed to Creative Intelligence.
- If both models fail, preserve attempt history and mark the job/video failed so the existing Retry action can be used.
- Manual retries append to the same video's attempt history.
- Users may select either Gemini model as the first attempt; the other configured Gemini model remains the fallback.

## Video input

Both models receive the local video file through the Gemini Files API. The adapter waits for the uploaded file to become ACTIVE, requests JSON output, reads token usage where available, and deletes the temporary Gemini file afterward.

## Environment variables

Add these backend-only values to the root `.env` file:
```env
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_ANALYSIS_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
```

Never commit the real `.env` file or expose provider keys to the frontend. NVIDIA credentials and NIM settings are not required.

## Database and API

Migration: `0010_analysis_model_attempts`.

- Adds final provider/model, total attempt count and total duration to `reference_videos`.
- Adds `reference_video_analysis_attempts` with one row per model attempt, including status, errors, duration, token usage and timestamps.
- Adds per-job optional primary provider/model fields.

Endpoint:
- `GET /api/v1/pages/{page_id}/reference-videos/{video_id}/analysis-attempts`

The endpoint is authenticated and scoped to the Page owner.

## UI

The Reference Intelligence submission form lets the user choose:
- Default order: Gemini 3.5 Flash-Lite, then Gemini 2.5 Flash
- Gemini 3.5 Flash-Lite as the first attempt
- Gemini 2.5 Flash as the first attempt

Automatic fallback remains enabled. Completed video cards show the final generating model and provide a model-attempt history panel.

## Operational notes

- Only `GEMINI_API_KEY` is needed for this analysis pipeline.
- A missing key, API error, timeout, malformed JSON, or invalid result is recorded as a failed attempt before the fallback is tried.
- Token and cost fields remain null when Gemini does not return usage or when a reliable cost cannot be calculated.
- The queue still requires one Celery worker with concurrency 1 to preserve strict FIFO processing.