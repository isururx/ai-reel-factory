from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.com", "www.fb.com"}
NON_PAGE_PATHS = {
    "watch", "reel", "reels", "photo", "photos", "posts", "videos",
    "groups", "events", "marketplace", "share", "stories", "story.php",
}


def normalize_facebook_page_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("Facebook Page URL is required.")
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlsplit(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host not in FACEBOOK_HOSTS:
        raise ValueError("Enter a public Facebook Page URL (https://www.facebook.com/...).")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Credentials and custom ports are not allowed in a Facebook URL.")
    path = "/" + "/".join(part for part in parsed.path.split("/") if part)
    first_segment = path.strip("/").split("/", 1)[0].lower() if path.strip("/") else ""
    if not first_segment or first_segment in NON_PAGE_PATHS:
        raise ValueError("Enter a Facebook Page URL, not a post, video, group, or feed URL.")
    # Keep only the stable Page identifier for profile.php links; drop tracking parameters.
    query = ""
    if first_segment == "profile.php":
        page_id = parse_qs(parsed.query).get("id", [None])[0]
        if not page_id or not page_id.isdigit():
            raise ValueError("For profile.php links, include a numeric id query parameter.")
        query = urlencode({"id": page_id})
    canonical_host = "www.facebook.com" if host.endswith("facebook.com") else "www.fb.com"
    return urlunsplit(("https", canonical_host, path.rstrip("/") or "/", query, ""))


class ReferencePageCreate(BaseModel):
    source_url: str = Field(min_length=8, max_length=2048)
    display_name: str | None = Field(default=None, max_length=160)
    notes: str = Field(default="", max_length=2000)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return normalize_facebook_page_url(value)


class ReferencePageUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"active", "paused"}:
            raise ValueError("Status must be active or paused.")
        return value


class ReferencePageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_id: int
    platform: str
    source_url: str
    normalized_url: str
    display_name: str | None
    notes: str
    status: str
    created_at: datetime
    updated_at: datetime
