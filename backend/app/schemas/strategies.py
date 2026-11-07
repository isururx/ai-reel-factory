from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    configuration: dict = Field(default_factory=dict)
class StrategyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version_number: int
    configuration: dict
    status: str
    created_at: datetime
class StrategyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    name: str
    description: str
    status: str
    created_at: datetime
