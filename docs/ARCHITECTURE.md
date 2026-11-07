# Architecture notes

## Core boundaries

- `frontend`: user interface only; never stores Meta tokens or provider secrets.
- `backend`: API, authorization, business rules, approvals and persistence.
- `workers` (future): asynchronous intelligence, media and publishing jobs.
- `gpu-worker` (future): independently deployable inference worker. The API must remain available when GPU capacity is offline.

## Tenant isolation

Every Page-owned record must be scoped to a `page_id`. Page-specific strategies, scripts, metrics, examples and credentials must never leak across Pages. Enforce this in database constraints and service-layer queries; add PostgreSQL row-level security before multi-user production deployment.

## Approval invariants

1. An approval applies to one immutable script or video version.
2. Editing creates a new version and invalidates the previous approval for the new version.
3. Publishing checks approval server-side against the exact video asset ID/version.
4. Retries use idempotency keys to avoid duplicate posts.

## Cost controls

GPU work must record provider, instance, start/end time, estimated and final cost, job ID and output artifact. Enforce a hard monthly budget before creating a rental; stop instances after work completes or a budget threshold is reached.

## Data and content safeguards

- Prefer original scripts and licensed/public-domain/owned media.
- Track sources for factual claims and require stronger verification for health, science, history and wildlife content.
- Do not assume competitor Page insights are available through Meta APIs; begin with owned Page data and permitted public trend sources.
