from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ReferenceVideo(Base):
    __tablename__ = "reference_videos"
    __table_args__ = (
        Index("ix_reference_videos_owner_reference", "owner_id", "reference_page_id"),
        Index("ix_reference_videos_owner_page", "owner_id", "page_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int | None] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=True, index=True)
    reference_page_id: Mapped[int | None] = mapped_column(ForeignKey("reference_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    reference_post_id: Mapped[int | None] = mapped_column(ForeignKey("reference_posts.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Reference video")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    views_count: Mapped[int | None] = mapped_column(Integer)
    reactions_count: Mapped[int | None] = mapped_column(Integer)
    shares_count: Mapped[int | None] = mapped_column(Integer)
    comments_count: Mapped[int | None] = mapped_column(Integer)
    manual_comments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    analysis_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    analysis_provider: Mapped[str | None] = mapped_column(String(40))
    analysis_model: Mapped[str | None] = mapped_column(String(160))
    analysis_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_total_duration_ms: Mapped[int | None] = mapped_column(Integer)
    analysis_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
