"""Background generation for durable, Page-scoped script batches."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.settings import settings
from app.database.session import SessionLocal
from app.models.content import ContentScript, ScriptVersion
from app.models.page import Page
from app.models.production_pipeline import ScriptBatch
from app.services.script_generation import generate_script
from app.worker import celery_app


@celery_app.task(name="script_batches.generate", bind=True)
def generate_script_batch(self, batch_id: int) -> dict:
    db = SessionLocal()
    try:
        batch = db.scalar(
            select(ScriptBatch)
            .where(ScriptBatch.id == batch_id)
            .with_for_update()
        )
        if batch is None:
            return {"status": "not_found", "batch_id": batch_id}
        # Protect against duplicate Celery deliveries creating duplicate scripts.
        if batch.status != "queued":
            return {"status": batch.status, "batch_id": batch_id}

        page = db.scalar(select(Page).where(
            Page.id == batch.page_id,
            Page.owner_id == batch.owner_id,
        ))
        if page is None:
            batch.status = "failed"
            batch.error_message = "The Page workspace no longer exists."
            batch.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed", "batch_id": batch_id}

        snapshot = dict(batch.input_snapshot or {})
        batch.status = "processing"
        batch.started_at = datetime.now(timezone.utc)
        db.commit()

        failures: list[str] = []
        patterns = snapshot.get("creative_patterns", [])
        for index in range(batch.requested_count):
            context = {
                "profile": snapshot["profile"],
                "strategy": snapshot["strategy"],
                "brief": snapshot["brief"],
                "source_url": snapshot.get("source_url"),
                "creative_patterns": patterns,
                "batch_instruction": (
                    f"Batch item {index + 1} of {batch.requested_count}. "
                    "Choose a distinct angle, story structure and hook; do not repeat "
                    "the same opening or narrative approach used by other items."
                ),
            }
            try:
                item = generate_script(context)
                script = ContentScript(
                    page_id=batch.page_id,
                    title=item["title"],
                    status="review",
                )
                script.versions.append(ScriptVersion(
                    version_number=1,
                    hook=item["hook"],
                    narration=item["narration"],
                    caption=item["caption"],
                    hashtags=item["hashtags"],
                    script_data={
                        **item["script_data"],
                        "title": item["title"],
                        "generation_provider": settings.llm_provider,
                        "generation_brief": snapshot["brief"],
                        "batch_id": batch.id,
                        "strategy_id": batch.strategy_id,
                        "strategy_version_id": batch.strategy_version_id,
                        "creative_pattern_ids": snapshot.get("creative_pattern_ids", []),
                    },
                ))
                db.add(script)
                db.flush()
                batch.completed_count += 1
                db.commit()
            except Exception as exc:
                db.rollback()
                # Reload the durable batch after rollback and persist this item's failure.
                batch = db.get(ScriptBatch, batch_id)
                failures.append(f"Item {index + 1}: {str(exc)[:500]}")
                batch.error_message = "\n".join(failures)[-4000:]
                db.commit()

        batch = db.get(ScriptBatch, batch_id)
        batch.completed_at = datetime.now(timezone.utc)
        if batch.completed_count == batch.requested_count:
            batch.status = "completed"
        elif batch.completed_count:
            batch.status = "partially_failed"
        else:
            batch.status = "failed"
        db.commit()
        return {
            "status": batch.status,
            "batch_id": batch.id,
            "requested_count": batch.requested_count,
            "completed_count": batch.completed_count,
        }
    finally:
        db.close()
