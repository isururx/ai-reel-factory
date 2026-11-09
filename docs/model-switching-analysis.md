# Video Analysis Model Switching

## Default provider order

The reference-video queue uses this order:

1. Google Gemini: `gemini-3.5-flash-lite`
2. NVIDIA NIM: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
3. Google Gemini: `gemini-2.5-flash`

The queue can optionally select a different primary provider/model for an individual video; the remaining configured providers are attempted after it.

## Behavior

- Fallback is immediate. There is no backoff or repeated attempt before switching providers.
- A provider failure, timeout, missing credential, malformed JSON response, or response missing a summary is recorded as a failed attempt.
- The first valid structured response wins.
- Only the successful response is passed to Creative Intelligence and saved as the final analysis.
- If every provider fails, the queue job becomes failed and the existing Retry analysis action can be used.
- A retry begins a new attempt sequence while preserving the prior attempt history.
- Attempt numbers are cumulative per video.

## Provider video input

### Gemini

Gemini receives the local video file through the Gemini Files API. The provider adapter waits for the uploaded file to become ACTIVE, requests JSON output, reads token usage where available, and deletes the temporary Gemini file afterward.

### NVIDIA Nemotron 3 Nano Omni

Nemotron receives a temporary, 30-minute Cloudflare R2 signed URL through NVIDIA NIM's OpenAI-compatible chat-completions API. The request passes the video as a `video_url` content part and enables `use_audio_in_video` so the model can inspect the embedded audio track as well as the video.

The model's documented input limit is MP4 video up to 2 minutes. NVIDIA documents sampling up to 1 FPS / 128 frames for 1080p and up to 2 FPS / 256 frames for lower-resolution 720p video. It supports video, audio, image and text input, and structured JSON output. The current Reel workflow targets 60–90 seconds, which fits the documented duration limit. Longer source videos may be rejected by Nemotron and will automatically fall through to Gemini 2.5 Flash. [NVIDIA model card](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning/modelcard) · [NIM API reference](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning)

The default API endpoint is `https://integrate.api.nvidia.com/v1`. Use the endpoint shown in your NVIDIA Build account if it differs.

## Environment variables

Add these backend-only values to the root `.env` file:

```env
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_ANALYSIS_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

NVIDIA_API_KEY=your_nvidia_build_api_key
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NEMOTRON_ANALYSIS_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
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
- Nemotron 3 Nano Omni 30B A3B
- Gemini 2.5 Flash

The selected model becomes the primary attempt. Automatic fallback remains enabled. Completed video cards show the final generating model and provide a model-attempt history panel.

## Operational notes

- Configure both Google and NVIDIA API keys to use the full chain.
- If a key is missing, that provider attempt is logged as failed and the orchestrator continues.
- Nemotron video input uses the stored R2 object and a valid temporary signed URL. The signed URL is generated only if the fallback reaches Nemotron.
- NVIDIA API trial quotas, rate limits and billing are controlled by NVIDIA; do not assume a free endpoint provides unlimited production capacity.
- Token and cost fields remain null when the provider does not return usage or when a reliable cost cannot be calculated.
- The queue still requires one Celery worker with concurrency 1 to preserve strict FIFO processing.
