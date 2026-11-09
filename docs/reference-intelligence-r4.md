# R4 — Advanced Creative Intelligence Engine

## What changes

R4 extends the existing reference-video analysis pipeline. The existing FIFO queue, Cloudflare R2 storage, Gemini Files API upload, and manual engagement context remain in place.

After Gemini analyzes a queued video, the worker now:
1. Stores the full multimodal analysis on the reference video.
2. Persists timestamped creative elements such as hooks, storytelling techniques, retention devices, editing, visual/audio techniques, emotional triggers, CTAs and endings.
3. Matches each element against patterns belonging only to the same owner and Page.
4. Adds source-video evidence, timestamps and manually supplied performance context.
5. Updates distinct supporting-video counts and pattern maturity automatically.

No human approval is required for extracted patterns. Patterns become `active` after they have been observed in at least three distinct reference videos on that Page. This is a repetition/maturity indicator, not proof that the pattern caused high performance.

## Database

Migration: `0008_creative_intelligence`

- `creative_elements`: individual observations from one video, including timestamps and evidence.
- `creative_patterns`: reusable techniques, scoped by `owner_id` and `page_id`.
- `pattern_evidence`: links each reusable pattern to the source creative element/video and its timestamps.

The pattern uniqueness constraint includes owner and Page. Fuzzy matching is restricted to the same owner, Page and category. No cross-Page pattern sharing or retrieval is performed.

## API

All routes require Supabase authentication and verify ownership of the Page workspace.

- `GET /api/v1/pages/{page_id}/creative-intelligence/summary`
- `GET /api/v1/pages/{page_id}/creative-intelligence/patterns`
  - Optional `category` and `status` filters.
- `GET /api/v1/pages/{page_id}/creative-intelligence/elements`
  - Optional `video_id`, `element_type`, and `limit`.
- `GET /api/v1/pages/{page_id}/creative-intelligence/patterns/{pattern_id}/evidence`

## UI

Open **Creative AI** from the main navigation. Select a Page workspace to see its independent pattern library, counts, categories, supporting videos and timestamped evidence. Submit new reference videos through the existing References page.

## Analysis quality and provenance

- Gemini is instructed to distinguish opening visual, narration and on-screen text.
- Hooks include the information gap, emotional trigger, promise and payoff.
- Elements should carry source timestamps and extraction confidence.
- Manual views/reactions/shares/comments are stored as user-supplied context, not verified platform data.
- Confidence measures extraction certainty, not expected virality.
- Repeated appearance does not establish causation or guarantee performance.
- Pattern descriptions are abstract creative techniques; source dialogue and distinctive expression must not be copied.

## Local setup

From the repository root:

```cmd
cd backend
.venv\Scripts\activate
python -m pip install -e .
python -m alembic upgrade head
python -m pytest
```

Restart the FastAPI API and the Celery worker after updating code.

## Current limitations

- Pattern matching currently uses normalized names and conservative string similarity, not embeddings.
- R4 does not yet inject patterns into script generation; that is the next integration milestone.
- The worker and live Gemini/R2 pipeline must be tested with real reference videos in the user's environment.
