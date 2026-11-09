from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


ALLOWED_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"}
MAX_FILESIZE = 300 * 1024 * 1024
MAX_DURATION_SECONDS = 15 * 60


class FacebookDownloadError(Exception):
    pass


def validate_facebook_url(url: str) -> None:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in ALLOWED_HOSTS:
        raise FacebookDownloadError("Enter a valid Facebook video or Reel URL.")
    if parsed.username or parsed.password:
        raise FacebookDownloadError("URLs containing credentials are not supported.")


def download_public_video(url: str) -> tuple[str, str, TemporaryDirectory]:
    """Download an accessible public Facebook video into a temporary directory.

    No cookies, login sessions, browser profiles, or access-control workarounds are used.
    The caller owns cleanup of the returned temporary directory.
    """
    validate_facebook_url(url)
    temp_dir = TemporaryDirectory(prefix="ai-reel-fb-")
    output_dir = Path(temp_dir.name)
    options = {
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        # Keep reference-analysis downloads lightweight; never fetch above 720p.
        "format": "best[height<=720][ext=mp4]/best[height<=720]",
        "merge_output_format": "mp4",
        "max_filesize": MAX_FILESIZE,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "match_filter": lambda info, incomplete: (
            "Video exceeds the 15-minute prototype limit."
            if info.get("duration") and info["duration"] > MAX_DURATION_SECONDS
            else None
        ),
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise FacebookDownloadError("Facebook did not provide downloadable video data.")
            candidates = [Path(item["filepath"]) for item in (info.get("requested_downloads") or []) if item.get("filepath")]
            candidates = [p for p in candidates if p.exists()]
            if not candidates:
                candidates = [p for p in output_dir.iterdir() if p.is_file()]
            if not candidates:
                raise FacebookDownloadError("No video file was produced.")
            video_path = candidates[0]
            if output_dir.resolve() not in video_path.resolve().parents:
                raise FacebookDownloadError("Unexpected download location.")
            title = str(info.get("title") or "facebook-video")[:160]
            return str(video_path), title, temp_dir
    except FacebookDownloadError:
        temp_dir.cleanup()
        raise
    except DownloadError as exc:
        temp_dir.cleanup()
        message = str(exc).lower()
        if "private" in message or "login" in message or "not available" in message:
            raise FacebookDownloadError(
                "This video is private, login-restricted, or unavailable. This prototype only "
                "supports videos accessible without signing in."
            ) from exc
        raise FacebookDownloadError(
            "Facebook could not provide this video. Check that the link is public and try again."
        ) from exc
    except Exception as exc:
        temp_dir.cleanup()
        raise FacebookDownloadError("The video could not be downloaded.") from exc
