"""Retrieve mature creative patterns and traceable evidence for one Page's scripts."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.creative_intelligence import CreativePattern, PatternEvidence


_STOP_WORDS = {
    "about", "after", "again", "also", "because", "before", "being", "between",
    "could", "from", "have", "into", "more", "most", "other", "over", "same",
    "some", "such", "than", "that", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "under", "very", "what", "when", "where",
    "which", "while", "with", "would", "your", "page", "video", "content",
}


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", value.lower())
        if token not in _STOP_WORDS
    }


def _pattern_relevance(pattern: CreativePattern, topic_tokens: set[str]) -> tuple[int, int, int, float]:
    pattern_tokens = _tokens(
        f"{pattern.name} {pattern.category} {pattern.description} {pattern.reusable_construction}"
    )
    overlap = len(pattern_tokens & topic_tokens)
    confidence = pattern.confidence_score or 0.0
    return (
        overlap,
        pattern.supporting_video_count,
        pattern.occurrence_count,
        confidence,
    )


def build_script_intelligence_context(
    db: Session,
    *,
    owner_id: str,
    page_id: int,
    trend_title: str,
    trend_summary: str,
    niche: str,
    target_audience: str,
    limit: int = 12,
) -> dict[str, Any]:
    """Return active patterns and compact evidence, strictly scoped to owner + Page.

    Pattern maturity means repeated observation across distinct reference videos;
    it must never be represented as proof of performance or virality.
    """
    patterns = list(db.scalars(
        select(CreativePattern).where(
            CreativePattern.owner_id == owner_id,
            CreativePattern.page_id == page_id,
            CreativePattern.status == "active",
        )
    ).all())

    topic_tokens = _tokens(f"{trend_title} {trend_summary} {niche} {target_audience}")
    patterns.sort(
        key=lambda item: _pattern_relevance(item, topic_tokens),
        reverse=True,
    )
    selected = patterns[:max(1, min(limit, 20))]

    prompt_patterns: list[dict[str, Any]] = []
    for pattern in selected:
        evidence_rows = list(db.scalars(
            select(PatternEvidence)
            .where(PatternEvidence.pattern_id == pattern.id)
            .order_by(PatternEvidence.created_at.desc(), PatternEvidence.id.desc())
            .limit(2)
        ).all())
        prompt_patterns.append({
            "pattern_id": pattern.id,
            "category": pattern.category,
            "name": pattern.name,
            "description": pattern.description,
            "reusable_construction": pattern.reusable_construction,
            "supporting_video_count": pattern.supporting_video_count,
            "occurrence_count": pattern.occurrence_count,
            "confidence_score": pattern.confidence_score,
            "evidence_examples": [
                {
                    "reference_video_id": evidence.reference_video_id,
                    "description": evidence.evidence_description,
                    "timestamp_start": evidence.timestamp_start,
                    "timestamp_end": evidence.timestamp_end,
                }
                for evidence in evidence_rows
            ],
        })

    provenance = {
        "retrieval_method": "page_scoped_active_patterns",
        "patterns_available": len(patterns),
        "patterns_used": [
            {
                "id": pattern["pattern_id"],
                "name": pattern["name"],
                "category": pattern["category"],
                "supporting_video_count": pattern["supporting_video_count"],
            }
            for pattern in prompt_patterns
        ],
    }
    return {"patterns": prompt_patterns, "provenance": provenance}
