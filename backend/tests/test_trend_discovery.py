from datetime import datetime, timedelta, timezone

from app.services.trend_discovery import _feed_entries, _score_for_page


def test_parse_rss_items_and_atom_entries():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>New discoveries in space science</title>
      <link>https://example.com/space</link>
      <description>Scientists report a new planet.</description>
      <pubDate>Sat, 07 Nov 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>"""
    entries = _feed_entries(xml)
    assert len(entries) == 1
    assert entries[0]["title"] == "New discoveries in space science"
    assert entries[0]["url"] == "https://example.com/space"
    assert entries[0]["published_at"] is not None


def test_page_relevance_scoring_rewards_niche_match_and_freshness():
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    old = datetime.now(timezone.utc) - timedelta(days=30)
    high, reason = _score_for_page(
        "New space science discovery", "Astronomy researchers found a planet.",
        "space science", "curious science fans", recent,
    )
    low, _ = _score_for_page(
        "Local gardening tips", "How to grow tomatoes.",
        "space science", "curious science fans", old,
    )
    assert high > low
    assert "Niche match" in reason
