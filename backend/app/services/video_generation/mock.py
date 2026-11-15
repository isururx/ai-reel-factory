from uuid import uuid4

from app.services.video_generation.base import VideoRenderRequest, VideoRenderResult


class MockVideoProvider:
    """Deterministic local adapter; simulates a completed render without creating a video file."""

    name = "mock"

    def render(self, request: VideoRenderRequest) -> VideoRenderResult:
        if not request.narration.strip():
            raise ValueError("The approved script has no narration to render.")
        render_id = f"mock-{uuid4().hex}"
        return VideoRenderResult(
            provider_job_id=render_id,
            output_object_key=f"mock://video-generation/{request.owner_id}/{request.page_id}/{render_id}.mp4",
            metadata={
                "provider": self.name,
                "simulation": True,
                "artifact_created": False,
                "message": "Mock render completed. No MP4 was generated or uploaded.",
                "script_version_id": request.script_version_id,
                "title": request.title,
            },
        )
