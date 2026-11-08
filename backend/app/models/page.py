from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Page(Base):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, default="facebook")
    external_page_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    profile: Mapped["PageProfile | None"] = relationship(back_populates="page", cascade="all, delete-orphan", uselist=False)
    strategies: Mapped[list["PageStrategy"]] = relationship(back_populates="page", cascade="all, delete-orphan")

class PageProfile(Base):
    __tablename__ = "page_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), unique=True, nullable=False)
    niche: Mapped[str] = mapped_column(String(120), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(40), nullable=False, default="English")
    tone: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    preferred_formats: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    restricted_topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    fact_check_level: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    page: Mapped[Page] = relationship(back_populates="profile")
