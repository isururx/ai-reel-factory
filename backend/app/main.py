from fastapi import FastAPI

from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-assisted content intelligence and Reel production API.",
)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
