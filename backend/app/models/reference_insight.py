from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReferenceCreativeInsight(Base):
    __tablename__ = "reference_creative_insights"
    __table_args__ = (
        Index("ix_reference_insights_owner_page_status", "owner_id", "page_id", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_video_id: Mapped[int] = mapped_column(ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type: Mapped[str] = mapped_column(String(60), nullable=False, default="creative_analysis")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    reviewer_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
