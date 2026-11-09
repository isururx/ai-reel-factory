# Video Analysis Model Switching

## Default provider order

The reference-video queue uses this order:

1. Google Gemini: `gemini-3.5-flash-lite`
2. Alibaba Cloud Model Studio: `qwen3.8-flash`
3. Google Gemini: `gemini-2.5-flash`

All model IDs are configurable in backend environment settings. The queue can optionally select a different primary provider/model for an individual video; the remaining configured providers are attempted after it.

## Behavior

- Fallback is immediate. There is no backoff or repeated attempt before switching to the next provider.
- A provider failure, timeout, missing credential, malformed JSON response, or response missing a summary is recorded as a failed attempt.
- The first valid structured response wins.
- Only the successful response is passed to Creative Intelligence and saved as the final analysis.
- If every provider fails, the queue job becomes failed and the existing Retry analysis action can be used.
- A retry begins a new attempt sequence while preserving the prior attempt history.
- Attempt numbers are cumulative per video.

## Provider video input

### Gemini

Gemini receives the local video file through the Gemini Files API. The provider adapter waits for the uploaded file to become ACTIVE, requests JSON output, reads token usage where available, and deletes the temporary Gemini file afterward.

### Qwen

Qwen receives a temporary, 30-minute Cloudflare R2 signed URL using the Model Studio OpenAI-compatible chat API and the `video_url` content type. The Qwen3.8 Flash visual-video input is treated as visual evidence; audio/narration claims must not be inferred when the selected model does not receive audio. The adapter requests a JSON object and captures token usage when returned.

The default international endpoint is `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`. Alibaba also provides workspace-specific Singapore endpoints; set `QWEN_BASE_URL` to the endpoint shown in the Model Studio workspace when using one.

## Environment variables

Add these backend-only values to the root `.env` file:

```env
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_ANALYSIS_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

QWEN_API_KEY=your_alibaba_model_studio_key
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_ANALYSIS_MODEL=qwen3.8-flash
```

Never commit the real `.env` file or expose provider keys to the frontend.

## Database and API

Migration: `0010_analysis_model_attempts`.

- Adds final provider/model, total attempt count and total duration to `reference_videos`.
- Adds `reference_video_analysis_attempts` with one row per provider attempt, including status, errors, duration, token usage and timestamps.
- Adds per-job optional primary provider/model fields.

Endpoint:
- `GET /api/v1/pages/{page_id}/reference-videos/{video_id}/analysis-attempts`

The endpoint is authenticated and scoped to the Page owner.

## UI

The Reference Intelligence submission form lets the user choose:
- Default provider order
- Gemini 3.5 Flash-Lite
- Qwen 3.8 Flash
- Gemini 2.5 Flash

The selected model becomes the primary attempt. Automatic fallback remains enabled. Completed video cards show the final generating model and provide a model-attempt history panel.

## Operational notes

- Configure both Google and Qwen API keys to use the full chain.
- If a key is missing, that provider attempt is logged as failed and the orchestrator continues.
- Qwen video input needs the stored R2 object and a valid temporary signed URL.
- Provider quotas, billing and model availability are controlled by their respective vendors. The application does not assume that a provider's free tier is always available.
- Token and cost fields remain null when the provider does not return usage or when a reliable cost cannot be calculated.
- The queue still requires one Celery worker with concurrency 1 to preserve strict FIFO processing.
