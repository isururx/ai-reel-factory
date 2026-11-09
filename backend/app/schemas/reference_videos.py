from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReferenceVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_page_id: int
    reference_post_id: int | None
    title: str
    source_url: str | None
    original_filename: str
    content_type: str
    file_size: int
    views_count: int | None
    reactions_count: int | None
    shares_count: int | None
    comments_count: int | None
    manual_comments: list[str]
    engagement_notes: str
    analysis_status: str
    analysis_result: dict
    created_at: datetime


class ReferenceVideoManualUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    views_count: int | None = Field(default=None, ge=0)
    reactions_count: int | None = Field(default=None, ge=0)
    shares_count: int | None = Field(default=None, ge=0)
    comments_count: int | None = Field(default=None, ge=0)
    manual_comments: list[str] | None = None
    engagement_notes: str | None = Field(default=None, max_length=10000)


class ReferenceInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    reference_video_id: int
    insight_type: str
    title: str
    content: dict
    review_status: str
    reviewer_notes: str
    created_at: datetime


class ReferenceInsightReview(BaseModel):
    review_status: str = Field(pattern="^(approved|rejected|pending_review)$")
    reviewer_notes: str = Field(default="", max_length=10000)
