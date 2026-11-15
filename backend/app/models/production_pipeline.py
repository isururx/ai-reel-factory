"""Durable production pipeline records. All records are Page-scoped."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ScriptBatch(Base):
    __tablename__ = "script_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("page_strategies.id", ondelete="RESTRICT"), nullable=False)
    strategy_version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id", ondelete="RESTRICT"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # automatic | manual
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class VideoProductionJob(Base):
    __tablename__ = "video_production_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("content_scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    script_version_id: Mapped[int] = mapped_column(ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="vast_ltx")
    provider_job_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    request_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_object_key: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PagePublishingSettings(Base):
    __tablename__ = "page_publishing_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    daily_reel_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    posting_slots: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    minimum_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    performance_optimisation_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScheduledPublication(Base):
    __tablename__ = "scheduled_publications"
    __table_args__ = (UniqueConstraint("page_id", "script_version_id", name="uq_publication_page_script_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    video_job_id: Mapped[int] = mapped_column(ForeignKey("video_production_jobs.id", ondelete="RESTRICT"), nullable=False, unique=True)
    script_version_id: Mapped[int] = mapped_column(ForeignKey("script_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled", index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    external_post_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    result_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
