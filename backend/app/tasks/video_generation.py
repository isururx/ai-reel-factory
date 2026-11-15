"""Asynchronous video generation for approved immutable script versions."""
from datetime import datetime, timezone

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.content import ScriptVersion
from app.models.production_pipeline import VideoProductionJob
from app.services.video_generation.base import VideoRenderRequest
from app.services.video_generation.factory import get_video_provider
from app.worker import celery_app


@celery_app.task(name="video_generation.render", bind=True, acks_late=True)
def render_video_job(self, job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.scalar(select(VideoProductionJob).where(VideoProductionJob.id == job_id))
        if job is None:
            return {"status": "not_found", "job_id": job_id}
        if job.status != "queued":
            return {"status": job.status, "job_id": job.id, "detail": "Job is not queued."}

        version = db.scalar(select(ScriptVersion).where(
            ScriptVersion.id == job.script_version_id,
            ScriptVersion.script_id == job.script_id,
        ))
        if version is None:
            raise RuntimeError("The approved script version could not be found.")

        # The immutable version is the render input; later script edits cannot alter this job.
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.attempt_count += 1
        db.commit()

        request = VideoRenderRequest(
            job_id=job.id,
            owner_id=job.owner_id,
            page_id=job.page_id,
            script_id=job.script_id,
            script_version_id=version.id,
            title=(version.script_data or {}).get("title") or "Untitled Reel",
            hook=version.hook,
            narration=version.narration,
            caption=version.caption,
            hashtags=version.hashtags or [],
            script_data=version.script_data or {},
        )
        provider = get_video_provider()
        result = provider.render(request)
        job.provider = provider.name
        job.provider_job_id = result.provider_job_id
        job.output_object_key = result.output_object_key
        job.request_snapshot = {
            **(job.request_snapshot or {}),
            "render_metadata": result.metadata,
        }
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = None
        db.commit()
        return {"status": job.status, "job_id": job.id, "provider": job.provider,
                "output_object_key": job.output_object_key, "metadata": result.metadata}
    except Exception as exc:
        db.rollback()
        job = db.get(VideoProductionJob, job_id)
        if job is not None:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(exc)[:2000]
            db.commit()
        return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}
    finally:
        db.close()
