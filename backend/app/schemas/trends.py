from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TrendFeedCollect(BaseModel):
    feed_urls: list[HttpUrl] = Field(min_length=1, max_length=20)


class TrendItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_name: str
    source_url: str
    title: str
    summary: str
    published_at: datetime | None
    collected_at: datetime
    source_metadata: dict


class TrendRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    trend_id: int
    score: float
    rationale: str
    status: str
    created_at: datetime
    trend: TrendItemRead


class TrendRecommendationUpdate(BaseModel):
    status: str = Field(pattern="^(saved|dismissed|selected)$")
