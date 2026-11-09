# R3 — AI Creative Analysis

R3 adds an on-demand multimodal analysis step to each ingested reference video.

## Flow

1. An authenticated user selects **Run AI analysis** in a Page's Reference Video Library.
2. The API verifies ownership of the Page, Reference Page, and video.
3. The backend downloads the private R2 object to a temporary local directory.
4. Gemini Files API receives the video. The backend waits for the file to become ACTIVE, submits a structured analysis prompt, and best-effort deletes the temporary Gemini file.
5. The structured result is saved to `reference_videos.analysis_result`.
6. A Page-scoped `reference_creative_insights` record is created with `pending_review` status.
7. A user can list insights for that Page and approve, reject, or leave them pending with reviewer notes.

## Analysis dimensions

- Summary and spoken-content summary
- Hook type and strength
- Story structure and approximate time references
- Visual style, shot types, pacing, and on-screen text
- Speech, music, and sound design
- Emotional tone and CTA
- Creative strengths and weaknesses
- Evidence observations with time references and confidence
- User-supplied engagement metrics and comment themes, clearly labelled as unverified context
- Reusable high-level patterns and original adaptation ideas
- Fact-check flags and overall confidence

The model is instructed not to invent reach, retention, audience demographics, exact quotes, or missing metrics, and not to reproduce distinctive scripts or dialogue.

## API

- `POST /api/v1/pages/{page_id}/references/{reference_id}/videos/{video_id}/analyze`
- `GET /api/v1/pages/{page_id}/reference-insights`
- `PATCH /api/v1/pages/{page_id}/reference-insights/{insight_id}/review`

Review payload example:

```json
{
  "review_status": "approved",
  "reviewer_notes": "Useful question-led hook pattern."
}
```

Allowed review states: `pending_review`, `approved`, `rejected`.

## Database

Migration `0007_reference_creative_insights` creates Page-scoped creative insight records. Apply it with:

```cmd
python -m alembic upgrade head
```

No new environment variable is required. Analysis uses the existing `GEMINI_API_KEY` and `LLM_MODEL`.

## Important limits

- Analysis is synchronous and can take a while because Gemini must upload/process the video before inference. Use a reverse-proxy/request timeout suitable for video analysis. A future job-queue milestone should move this work to a background worker.
- Gemini Files API receives a temporary copy of the video. The application requests deletion after analysis; cleanup is best-effort.
- The current milestone stores structured Page-specific insights but does not yet use embeddings or automatically inject them into script generation. That is the next R4 retrieval integration.
- Human review is required before insights become approved creative guidance.
