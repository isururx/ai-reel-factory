from app.core.settings import settings
from app.services.video_generation.mock import MockVideoProvider


def get_video_provider():
    provider = settings.video_provider.strip().lower()
    if provider == "mock":
        return MockVideoProvider()
    raise ValueError(
        f"Unsupported VIDEO_PROVIDER '{settings.video_provider}'. "
        "Only 'mock' is currently implemented; configure a real provider after its adapter is added."
    )
