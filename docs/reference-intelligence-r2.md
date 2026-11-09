# R2 — Reference post collection and performance snapshots

R2 adds the storage and API layer for collecting public Facebook Page post metadata through Meta's Graph API.

## What is included

- Reference post records keyed by the external Meta post ID.
- Immutable metric snapshots for available reactions, comments and shares.
- Authenticated endpoints scoped to the signed-in owner and selected Page workspace.
- A manual "Collect latest posts" action in the Reference Intelligence UI.
- A per-reference comparison index: known interactions (reactions + comments + shares) divided by the median known interaction count for the collected posts on that same reference Page, multiplied by 100.
- Links back to original posts; no third-party video download or reposting.

The index is a relative interaction score, **not an engagement rate**. Public competitor reach, impressions, retention and watch time are not assumed to be available. Missing metrics remain null and are not silently treated as zero.

## API

- `POST /api/v1/pages/{page_id}/references/{reference_id}/collect?limit=25`
- `GET /api/v1/pages/{page_id}/references/{reference_id}/posts?limit=50`

Collection is blocked for paused references. All queries verify the reference belongs to the authenticated owner and requested workspace.

## Meta setup

Meta collection is disabled until a suitable backend-only token is configured. After the app has the necessary Meta feature approval and token access, add these values to the backend root `.env`:

```env
META_ACCESS_TOKEN=your_server_side_meta_access_token
META_GRAPH_API_VERSION=v26.0
```

Never place this token in `frontend/.env.local`, browser code, or Git. Use a token type supported for Page Public Content Access in your app's approved configuration. The Graph API version is configurable because Meta versions change.

Meta's Page reference documentation describes PPCA/PPMA as the feature access route for public Page data and notes system-user tokens for PPCA usage. Verify the exact token requirements in your app's current Meta dashboard and docs before production use.

## Apply locally

The R2 migration depends on R1 migration `0004_reference_pages`, so the R1 branch must be merged or checked out first.

```cmd
cd backend
python -m alembic upgrade head
python -m pytest
```

Restart the backend and frontend, open **References**, and select **View collected posts** for a saved reference. Without Meta credentials, the collection endpoint returns a clear 503 response; the saved reference registry and posts screen remain usable.
