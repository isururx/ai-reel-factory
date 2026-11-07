from fastapi import FastAPI
from app.api.routes.pages import router as pages_router
from app.api.routes.strategies import router as strategies_router
from app.core.settings import settings
app = FastAPI(title=settings.app_name, version="0.2.0", description="AI-assisted content intelligence and Reel production API.")
app.include_router(pages_router, prefix="/api/v1")
app.include_router(strategies_router, prefix="/api/v1")
@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}
@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
