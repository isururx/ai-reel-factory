# M7 — Intelligence-Driven Script Generation

## Goal

Connect the existing M6 Gemini script-generation workflow to the R4 Page-specific Creative Intelligence Engine. Script generation remains initiated from a selected Page trend recommendation, but the prompt now includes mature creative patterns and compact supporting evidence belonging only to that Page.

## Retrieval behavior

Before calling the LLM, the API retrieves patterns matching all of these conditions:

- `owner_id` matches the authenticated user.
- `page_id` matches the selected Page.
- `status` is `active`.

Patterns are ranked using topic-token overlap with the trend title/summary and Page niche/audience, followed by supporting-video count, occurrence count and extraction confidence. At most 12 patterns are sent to the model.

For each selected pattern, the latest evidence records from up to two distinct supporting videos are included with their source video IDs and timestamps. Raw observed dialogue is not sent as reusable script material.

## Prompt rules

Gemini is instructed to:

- Use only patterns relevant to the selected trend and audience.
- Adapt abstract techniques with original wording and examples.
- Never copy reference-video dialogue, distinctive phrasing or exact sequences.
- Treat supporting-video counts as repetition evidence, not proof of performance.
- Treat extraction confidence as confidence in the analysis, not a virality prediction.
- Generate normally from the Page profile, strategy and trend when no mature patterns exist.
- Keep all three variations meaningfully different.

## Provenance

Every saved script version records a `creative_intelligence` object in `script_data`:

- retrieval method
- number of active patterns available
- pattern IDs, names, categories and supporting-video counts actually supplied to Gemini

The Script Studio displays these patterns so a reviewer can understand which Page-specific techniques informed a variation.

## API and database

The existing M6 endpoint remains unchanged:

`POST /api/v1/pages/{page_id}/trends/{recommendation_id}/generate-scripts`

No database migration is required. Pattern retrieval is read-only and uses the existing `creative_patterns` and `pattern_evidence` tables.

## Important limitations

- Current retrieval uses lightweight lexical overlap and maturity/support counts, not embeddings or semantic search.
- Active means observed in at least three distinct reference videos; it does not mean successful or high-performing.
- User-entered performance metrics remain unverified context.
- Human review and fact-checking are still required before production.
- If a Page has no active patterns, M6 behavior remains available without blocking script generation.

## Validation

Run locally from the repository root:

```cmd
cd backend
python -m pytest
```

Then:

```cmd
cd frontend
npm run build
```

Test with two Pages that have different active patterns and verify each Page's generated script provenance contains only its own pattern IDs.
