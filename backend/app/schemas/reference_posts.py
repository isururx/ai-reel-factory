from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReferencePostMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reactions_count: int | None
    comments_count: int | None
    shares_count: int | None
    captured_at: datetime
    available_fields: list[str]


class ReferencePostRead(BaseModel):
    id: int
    external_post_id: str
    message: str
    permalink_url: str | None
    media_type: str | None
    created_time: datetime | None
    latest_metrics: ReferencePostMetricRead | None = None
    interaction_count: int | None = None
    performance_score: float | None = None


class ReferenceCollectionResult(BaseModel):
    reference_page_id: int
    status: str
    collected_posts: int
    updated_posts: int
    message: str
