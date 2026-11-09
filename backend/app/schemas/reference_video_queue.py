from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ReferenceVideoQueueCreate(BaseModel):
    source_url: HttpUrl
    title: str = Field(default="Reference video", max_length=200)
    views_count: int | None = Field(default=None, ge=0)
    reactions_count: int | None = Field(default=None, ge=0)
    shares_count: int | None = Field(default=None, ge=0)
    comments_count: int | None = Field(default=None, ge=0)
    manual_comments: list[str] = Field(default_factory=list, max_length=200)
    engagement_notes: str = Field(default="", max_length=10000)
    analysis_primary_provider: str | None = Field(default=None, pattern="^gemini$")
    analysis_primary_model: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_primary_model(self):
        if bool(self.analysis_primary_provider) != bool(self.analysis_primary_model):
            raise ValueError("Choose both analysis_primary_provider and analysis_primary_model.")
        allowed = {
            ("gemini", "gemini-3.5-flash-lite"),
            ("gemini", "gemini-2.5-flash"),
        }
        if self.analysis_primary_provider and (self.analysis_primary_provider, self.analysis_primary_model) not in allowed:
            raise ValueError("Unsupported primary analysis model selection.")
        return self


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
    analysis_primary_provider: str | None = None
    analysis_primary_model: str | None = None


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
    analysis_provider: str | None = None
    analysis_model: str | None = None
    analysis_attempt_count: int = 0
    analysis_total_duration_ms: int | None = None
    analyzed_at: datetime | None
    created_at: datetime
