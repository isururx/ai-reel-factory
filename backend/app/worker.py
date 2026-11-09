from celery import Celery

from app.core.settings import settings

celery_app = Celery(
    "ai_reel_factory",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.reference_video_queue"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
