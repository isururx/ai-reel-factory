from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VideoProductionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    script_id: int
    script_version_id: int
    status: str
    provider: str
    provider_job_id: str | None
    request_snapshot: dict
    output_object_key: str | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
