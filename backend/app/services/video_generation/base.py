from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VideoRenderRequest:
    job_id: int
    owner_id: str
    page_id: int
    script_id: int
    script_version_id: int
    title: str
    hook: str
    narration: str
    caption: str
    hashtags: list[str]
    script_data: dict


@dataclass(frozen=True)
class VideoRenderResult:
    provider_job_id: str
    output_object_key: str
    metadata: dict


class VideoGenerationProvider(Protocol):
    name: str

    def render(self, request: VideoRenderRequest) -> VideoRenderResult:
        """Render one approved script version and return its durable output reference."""
