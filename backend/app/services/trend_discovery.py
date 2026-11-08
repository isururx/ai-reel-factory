import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.page import Page, PageProfile
from app.models.trend import PageTrendRecommendation, TrendItem


STOP_WORDS = {
    "about", "after", "again", "against", "also", "among", "because", "before",
    "being", "between", "could", "from", "have", "into", "more", "most", "other",
    "over", "same", "should", "some", "such", "than", "that", "their", "there",
    "these", "they", "this", "those", "through", "under", "very", "what", "when",
    "where", "which", "while", "with", "would", "your", "https", "http", "www",
}


def _words(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]{3,}", value.lower()) if word not in STOP_WORDS}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _feed_entries(xml_content: bytes) -> list[dict]:
    root = ET.fromstring(xml_content)
    entries = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        fields = {}
        link = ""
        for child in list(element):
            key = child.tag.rsplit("}", 1)[-1]
            value = "".join(child.itertext()).strip()
            if key == "link":
                link = child.attrib.get("href") or value or link
            elif key not in fields and value:
                fields[key] = value
        title = fields.get("title", "").strip()
        if title and link.startswith(("http://", "https://")):
            entries.append({
                "title": title[:500],
                "url": link[:2048],
                "summary": (fields.get("description") or fields.get("summary") or fields.get("content") or "")[:5000],
                "published_at": _parse_date(fields.get("pubDate") or fields.get("published") or fields.get("updated")),
            })
    return entries


def _score_for_page(title: str, summary: str, niche: str, audience: str, published_at: datetime | None) -> tuple[float, str]:
    words = _words(f"{title} {summary}")
    niche_hits = sorted(words & _words(niche))
    audience_hits = sorted(words & _words(audience))
    denominator = max(1, min(4, len(_words(niche)) + len(_words(audience))))
    relevance = min(1.0, (len(niche_hits) * 0.7 + len(audience_hits) * 0.3) / denominator)
    freshness = 0.35
    if published_at:
        age_hours = max(0.0, (datetime.now(timezone.utc) - published_at.astimezone(timezone.utc)).total_seconds() / 3600)
        freshness = max(0.0, 1.0 - age_hours / (24 * 14))
    score = round(100 * (0.75 * relevance + 0.25 * freshness), 1)
    reasons = []
    if niche_hits:
        reasons.append("Niche match: " + ", ".join(niche_hits[:4]))
    if audience_hits:
        reasons.append("Audience match: " + ", ".join(audience_hits[:3]))
    if not niche_hits and not audience_hits:
        reasons.append("Low direct keyword overlap; manually review broader relevance")
    reasons.append("Freshness: " + ("recent" if freshness >= 0.7 else "older or undated"))
    return score, ". ".join(reasons)


def collect_rss_feeds(db: Session, owner_id: str, feed_urls: list[str]) -> dict:
    pages = list(db.scalars(select(Page).where(Page.owner_id == owner_id, Page.is_active.is_(True))).all())
    profiles = {
        p.page_id: p for p in db.scalars(
            select(PageProfile).where(PageProfile.page_id.in_([page.id for page in pages]))
        ).all()
    } if pages else {}
    created = updated = 0
    errors = []

    for feed_url in feed_urls:
        parsed = urlparse(feed_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append({"feed_url": feed_url, "error": "Only HTTP(S) feed URLs are allowed."})
            continue
        try:
            response = httpx.get(
                feed_url, timeout=12.0, follow_redirects=True,
                headers={"User-Agent": "AI-Reel-Factory/0.1"},
            )
            response.raise_for_status()
            entries = _feed_entries(response.content)
            source_name = parsed.hostname or "RSS"
            for entry in entries:
                item = db.scalar(select(TrendItem).where(
                    TrendItem.owner_id == owner_id, TrendItem.source_url == entry["url"]
                ))
                if item is None:
                    item = TrendItem(
                        owner_id=owner_id, source_name=source_name, source_url=entry["url"],
                        title=entry["title"], summary=entry["summary"],
                        published_at=entry["published_at"], source_metadata={"feed_url": feed_url},
                    )
                    db.add(item)
                    db.flush()
                    created += 1
                else:
                    item.title, item.summary = entry["title"], entry["summary"]
                    item.published_at = entry["published_at"]
                    updated += 1

                for page in pages:
                    profile = profiles.get(page.id)
                    if profile is None:
                        continue
                    score, rationale = _score_for_page(
                        item.title, item.summary, profile.niche, profile.target_audience, item.published_at
                    )
                    rec = db.scalar(select(PageTrendRecommendation).where(
                        PageTrendRecommendation.page_id == page.id,
                        PageTrendRecommendation.trend_id == item.id,
                    ))
                    if rec is None:
                        db.add(PageTrendRecommendation(
                            page_id=page.id, trend_id=item.id, score=score, rationale=rationale
                        ))
                    elif rec.status == "suggested":
                        rec.score, rec.rationale = score, rationale
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            errors.append({"feed_url": feed_url, "error": str(exc)[:300]})
    db.commit()
    return {
        "created": created, "updated": updated,
        "feeds_processed": len(feed_urls) - len(errors), "errors": errors,
    }
