# Development roadmap

## M0 — Foundation
- [x] Monorepo scaffold
- [x] FastAPI health endpoint
- [x] Next.js dashboard shell
- [x] Docker Compose for PostgreSQL/pgvector and Redis
- [ ] Verify local startup on the developer machine

## M1 — Single-Page workspace
- Page profile and audience definition
- Page-specific content strategy with versioning
- Database migrations and seed data
- Basic dashboard navigation

## M2 — Content intelligence
- Import the connected Page's own permitted post/insight data
- Store time-based metric snapshots
- Classify content format, hook, topic and storytelling pattern
- Trend ingestion from permitted sources
- Generate Page-specific opportunities and strategy proposals

## M3 — Script studio
- Provider-independent LLM interface
- Retrieve only examples belonging to the selected Page
- Generate three script variations
- Evaluate and edit scripts
- Immutable script versions and approval events

## M4 — Video production
- Queue and worker contract
- Cost-aware GPU provider adapter
- Benchmark candidate models before choosing one
- TTS, subtitles, FFmpeg assembly and quality checks
- Immutable video assets and review UI

## M5 — Publishing and feedback
- Meta OAuth and Page token storage
- Permission-aware publishing integration
- Server-side approval validation
- Idempotent publishing jobs
- Metric collection and learning loop

## M6 — Scale
- Add additional Pages with tenant isolation tests
- Per-Page quotas and schedules
- GPU budget enforcement and auto-shutdown
- Load, recovery and duplicate-publish tests
