from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TrendItem(Base):
    __tablename__ = "trend_items"
    __table_args__ = (
        UniqueConstraint("owner_id", "source_url", name="uq_trend_owner_source_url"),
        Index("ix_trend_owner_collected", "owner_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    recommendations: Mapped[list["PageTrendRecommendation"]] = relationship(
        back_populates="trend", cascade="all, delete-orphan"
    )


class PageTrendRecommendation(Base):
    __tablename__ = "page_trend_recommendations"
    __table_args__ = (
        UniqueConstraint("page_id", "trend_id", name="uq_page_trend_recommendation"),
        Index("ix_page_trend_status_score", "page_id", "status", "score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    trend_id: Mapped[int] = mapped_column(ForeignKey("trend_items.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trend: Mapped[TrendItem] = relationship(back_populates="recommendations")
