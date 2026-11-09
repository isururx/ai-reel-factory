from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CreativeElementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_video_id: int
    element_type: str
    name: str
    description: str
    start_seconds: float | None
    end_seconds: float | None
    observed_text: str
    reusable_construction: str
    attributes: dict
    confidence_score: float | None
    created_at: datetime


class CreativePatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    category: str
    name: str
    description: str
    reusable_construction: str
    occurrence_count: int
    supporting_video_count: int
    confidence_score: float | None
    status: str
    last_observed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PatternEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pattern_id: int
    creative_element_id: int
    reference_video_id: int
    evidence_description: str
    timestamp_start: float | None
    timestamp_end: float | None
    performance_context: dict
    created_at: datetime
