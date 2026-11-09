from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ReferenceVideoQueueCreate(BaseModel):
    source_url: HttpUrl
    title: str = Field(default="Reference video", max_length=200)
    views_count: int | None = Field(default=None, ge=0)
    reactions_count: int | None = Field(default=None, ge=0)
    shares_count: int | None = Field(default=None, ge=0)
    comments_count: int | None = Field(default=None, ge=0)
    manual_comments: list[str] = Field(default_factory=list, max_length=200)
    engagement_notes: str = Field(default="", max_length=10000)


class ReferenceVideoQueueJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    source_url: str
    title: str
    views_count: int | None
    reactions_count: int | None
    shares_count: int | None
    comments_count: int | None
    status: str
    queue_position: int | None
    reference_video_id: int | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ReferenceVideoQueueJobList(BaseModel):
    jobs: list[ReferenceVideoQueueJobRead]
    queued_count: int
    processing_count: int


class ReferenceVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int | None
    reference_page_id: int | None
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
    analyzed_at: datetime | None
    created_at: datetime
