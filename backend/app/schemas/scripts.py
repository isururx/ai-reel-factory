from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

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
