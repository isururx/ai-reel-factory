from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.pages import router as pages_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.trends import router as trends_router
from app.api.routes.scripts import router as scripts_router
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="AI-assisted content intelligence and Reel production API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list({settings.frontend_origin, "http://127.0.0.1:3000"}),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(pages_router, prefix="/api/v1")
app.include_router(strategies_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(scripts_router, prefix="/api/v1")


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
