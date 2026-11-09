from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ReferencePost(Base):
    __tablename__ = "reference_posts"
    __table_args__ = (
        UniqueConstraint("reference_page_id", "external_post_id", name="uq_reference_post_external"),
        Index("ix_reference_posts_owner_reference_created", "owner_id", "reference_page_id", "created_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reference_page_id: Mapped[int] = mapped_column(ForeignKey("reference_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    external_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    permalink_url: Mapped[str | None] = mapped_column(String(2048))
    media_type: Mapped[str | None] = mapped_column(String(40))
    created_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metrics: Mapped[list["ReferencePostMetric"]] = relationship(back_populates="post", cascade="all, delete-orphan")


class ReferencePostMetric(Base):
    __tablename__ = "reference_post_metrics"
    __table_args__ = (
        UniqueConstraint("post_id", "captured_at", name="uq_reference_post_metric_snapshot"),
        Index("ix_reference_post_metrics_post_captured", "post_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("reference_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    reactions_count: Mapped[int | None] = mapped_column(Integer)
    comments_count: Mapped[int | None] = mapped_column(Integer)
    shares_count: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    available_fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    post: Mapped[ReferencePost] = relationship(back_populates="metrics")
