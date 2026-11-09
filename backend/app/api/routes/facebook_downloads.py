import re
from pathlib import Path
import shutil

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, HttpUrl

from app.core.auth import CurrentUser
from app.services.facebook_downloader import FacebookDownloadError, download_public_video

router = APIRouter(prefix="/downloads", tags=["video downloads"])


class FacebookDownloadRequest(BaseModel):
    url: HttpUrl


@router.post("/facebook")
def download_facebook_video(payload: FacebookDownloadRequest, _user: CurrentUser):
    try:
        file_path, title, temp_dir = download_public_video(str(payload.url))
    except FacebookDownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safe_title = re.sub(r"[^A-Za-z0-9._ -]+", "", title).strip(" .")[:80] or "facebook-video"
    return FileResponse(
        path=file_path,
        media_type="video/mp4" if Path(file_path).suffix.lower() == ".mp4" else "video/webm",
        filename=f"{safe_title}{Path(file_path).suffix}",
        background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
    )
