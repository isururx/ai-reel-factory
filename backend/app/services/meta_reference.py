from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
import httpx
from fastapi import HTTPException
from app.core.settings import settings


def _page_identifier(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.path.rstrip("/").endswith("profile.php"):
        return parse_qs(parsed.query).get("id", [""])[0]
    return parsed.path.strip("/").split("/")[0]


async def collect_public_page_posts(source_url: str, limit: int = 25) -> list[dict]:
    token = settings.meta_access_token
    if not token:
        raise HTTPException(status_code=503, detail="Meta collection is not configured yet. Add META_ACCESS_TOKEN on the backend after the required Meta access is approved.")
    version = settings.meta_graph_api_version
    identifier = _page_identifier(source_url)
    if not identifier:
        raise HTTPException(status_code=422, detail="Could not determine the Facebook Page identifier from this URL.")
    base = f"https://graph.facebook.com/{version}"
    timeout = httpx.Timeout(25.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        common = {"access_token": token}
        try:
            page = await client.get(f"{base}/{identifier}", params={**common, "fields": "id,name"})
            page.raise_for_status()
            page_data = page.json()
            page_id = page_data["id"]
            response = await client.get(
                f"{base}/{page_id}/posts",
                params={
                    **common,
                    "limit": min(max(limit, 1), 50),
                    "fields": "id,message,created_time,permalink_url,type,shares,reactions.limit(0).summary(true),comments.limit(0).summary(true)",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            detail = "Meta Graph API request failed."
            try:
                error = exc.response.json().get("error", {})
                detail = error.get("message") or detail
            except Exception:
                pass
            raise HTTPException(status_code=502, detail=f"{detail} Check Meta app access, Page Public Content Access approval, token permissions, and API version.")
        except (httpx.RequestError, KeyError, ValueError):
            raise HTTPException(status_code=502, detail="Could not reach or parse the Meta Graph API response.")
    posts = []
    for item in payload.get("data", []):
        reactions = item.get("reactions", {}).get("summary", {}).get("total_count")
        comments = item.get("comments", {}).get("summary", {}).get("total_count")
        shares = item.get("shares", {}).get("count")
        posts.append({
            "external_post_id": item["id"],
            "message": item.get("message", ""),
            "permalink_url": item.get("permalink_url"),
            "media_type": item.get("type"),
            "created_time": datetime.fromisoformat(item["created_time"].replace("Z", "+00:00")) if item.get("created_time") else None,
            "reactions_count": reactions,
            "comments_count": comments,
            "shares_count": shares,
            "available_fields": [key for key, value in {
                "reactions": reactions, "comments": comments, "shares": shares
            }.items() if value is not None],
            "raw": {"page_id": page_id},
        })
    return posts
