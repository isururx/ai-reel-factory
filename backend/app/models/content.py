from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class ContentScript(Base):
    __tablename__ = "content_scripts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    versions: Mapped[list["ScriptVersion"]] = relationship(back_populates="script", cascade="all, delete-orphan")

class ScriptVersion(Base):
    __tablename__ = "script_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("content_scripts.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hook: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hashtags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    script_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    script: Mapped[ContentScript] = relationship(back_populates="versions")
    approvals: Mapped[list["ApprovalEvent"]] = relationship(back_populates="script_version", cascade="all, delete-orphan")

class ApprovalEvent(Base):
    __tablename__ = "approval_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    script_version_id: Mapped[int] = mapped_column(ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(120), nullable=False, default="owner")
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    script_version: Mapped[ScriptVersion] = relationship(back_populates="approvals")
