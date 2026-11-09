from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CreativeElement(Base):
    """An observable creative element extracted from one reference video."""
    __tablename__ = "creative_elements"
    __table_args__ = (
        Index("ix_creative_elements_page_video", "owner_id", "page_id", "reference_video_id"),
        Index("ix_creative_elements_type", "owner_id", "page_id", "element_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_video_id: Mapped[int] = mapped_column(ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False, index=True)
    element_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_seconds: Mapped[float | None] = mapped_column(Float)
    end_seconds: Mapped[float | None] = mapped_column(Float)
    observed_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reusable_construction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreativePattern(Base):
    """A reusable, automatically available technique scoped to one Page."""
    __tablename__ = "creative_patterns"
    __table_args__ = (
        UniqueConstraint("owner_id", "page_id", "normalized_key", name="uq_creative_pattern_page_key"),
        Index("ix_creative_patterns_page_status", "owner_id", "page_id", "status"),
        Index("ix_creative_patterns_page_category", "owner_id", "page_id", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reusable_construction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supporting_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="emerging")
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PatternEvidence(Base):
    """Traceable evidence connecting a Page pattern to a source video element."""
    __tablename__ = "pattern_evidence"
    __table_args__ = (
        UniqueConstraint("pattern_id", "creative_element_id", name="uq_pattern_evidence_element"),
        Index("ix_pattern_evidence_video", "reference_video_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("creative_patterns.id", ondelete="CASCADE"), nullable=False, index=True)
    creative_element_id: Mapped[int] = mapped_column(ForeignKey("creative_elements.id", ondelete="CASCADE"), nullable=False)
    reference_video_id: Mapped[int] = mapped_column(ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False)
    evidence_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timestamp_start: Mapped[float | None] = mapped_column(Float)
    timestamp_end: Mapped[float | None] = mapped_column(Float)
    performance_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
