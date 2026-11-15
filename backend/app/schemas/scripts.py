from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ScriptGenerateRequest(BaseModel):
    brief: str | None = Field(default=None, min_length=20, max_length=5000)
    source_url: HttpUrl | None = None


class ScriptBatchCreate(BaseModel):
    strategy_id: int
    strategy_version_id: int
    brief: str = Field(min_length=20, max_length=5000)
    source_url: HttpUrl | None = None
    mode: Literal["automatic", "manual"] = "automatic"
    pattern_selection: Literal["automatic", "manual", "hybrid"] = "automatic"
    pattern_ids: list[int] = Field(default_factory=list, max_length=20)
    script_count: int | None = Field(default=1, ge=1, le=20)
    fill_remaining_daily_slots: bool = False


class ScriptBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    strategy_id: int
    strategy_version_id: int
    mode: str
    status: str
    requested_count: int
    completed_count: int
    input_snapshot: dict
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class ScriptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version_number: int
    hook: str
    narration: str
    caption: str
    hashtags: list
    script_data: dict
    created_at: datetime


class ContentScriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    title: str
    status: str
    created_at: datetime
    versions: list[ScriptVersionRead]


class ScriptVersionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    hook: str = Field(min_length=1, max_length=500)
    narration: str = Field(min_length=1)
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list, max_length=20)


class ScriptDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    comments: str = Field(default="", max_length=2000)
