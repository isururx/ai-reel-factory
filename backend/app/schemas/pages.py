from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class PageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    platform: str = Field(default="facebook", min_length=1, max_length=30)
    external_page_id: str | None = Field(default=None, max_length=128)

class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    platform: str
    external_page_id: str | None
    is_active: bool
    created_at: datetime

class PageProfileUpsert(BaseModel):
    niche: str = Field(min_length=1, max_length=120)
    target_audience: str = Field(default="", max_length=500)
    language: str = Field(default="English", max_length=40)
    tone: dict = Field(default_factory=dict)
    preferred_formats: list[str] = Field(default_factory=list)
    restricted_topics: list[str] = Field(default_factory=list)
    fact_check_level: str = Field(default="standard", max_length=30)

class PageProfileRead(PageProfileUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    updated_at: datetime
