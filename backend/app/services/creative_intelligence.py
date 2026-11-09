"""Persist timestamped creative observations and consolidate Page-local patterns."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.creative_intelligence import CreativeElement, CreativePattern, PatternEvidence
from app.models.reference_video import ReferenceVideo


ALLOWED_TYPES = {
    "hook", "storytelling", "retention", "editing", "visual", "audio",
    "emotional", "information_delivery", "cta", "ending", "other",
}


def _text(value: Any, limit: int = 4000) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    return None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _confidence(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        score = float(value)
        if 0 <= score <= 1:
            return score
        if 1 <= score <= 10:
            return score / 10
    if isinstance(value, str):
        return {"low": 0.35, "medium": 0.65, "high": 0.9}.get(value.lower())
    return None


def _extract_candidates(analysis: dict) -> list[dict]:
    raw = analysis.get("creative_elements")
    candidates = list(raw) if isinstance(raw, list) else []

    hook = analysis.get("hook_analysis")
    has_hook_element = any(isinstance(item, dict) and item.get("element_type") == "hook" for item in candidates)
    if isinstance(hook, dict) and not has_hook_element:
        hook_type = _text(hook.get("hook_type")) or "other"
        candidates.append({
            "element_type": "hook",
            "name": f"{hook_type.replace('_', ' ').title()} Hook",
            "description": _text(hook.get("information_gap")),
            "start_seconds": hook.get("start_seconds", 0),
            "end_seconds": hook.get("end_seconds"),
            "observed_text": _text(hook.get("opening_text") or hook.get("opening_narration"), 2000),
            "observed_visual": _text(hook.get("opening_visual"), 1000),
            "reusable_construction": "Create an opening that establishes this information gap: "
                + _text(hook.get("information_gap"), 700)
                + ". Promise/payoff: " + _text(hook.get("promise"), 400),
            "emotional_triggers": hook.get("emotional_trigger", []),
            "confidence": hook.get("confidence"),
        })

    # Backward compatibility for analyses saved before the structured schema.
    if not candidates:
        old_hook = analysis.get("hook")
        if isinstance(old_hook, dict) and (_text(old_hook.get("description")) or _text(old_hook.get("type"))):
            candidates.append({
                "element_type": "hook",
                "name": _text(old_hook.get("name")) or _text(old_hook.get("type")) or "Detected hook",
                "description": _text(old_hook.get("description")),
                "start_seconds": 0,
                "end_seconds": 10,
                "reusable_construction": _text(old_hook.get("reusable_construction")) or _text(old_hook.get("technique")),
                "confidence": old_hook.get("confidence", old_hook.get("strength")),
            })
        old_patterns = analysis.get("reusable_patterns")
        if isinstance(old_patterns, list):
            for item in old_patterns:
                if isinstance(item, dict):
                    candidates.append({
                        "element_type": item.get("category", "storytelling"),
                        "name": item.get("name") or item.get("pattern"),
                        "description": item.get("description") or item.get("why_it_may_work"),
                        "reusable_construction": item.get("reusable_construction") or item.get("adaptation_idea"),
                        "start_seconds": item.get("start_seconds"),
                        "end_seconds": item.get("end_seconds"),
                        "confidence": item.get("confidence"),
                    })
    return candidates


def persist_creative_intelligence(
    db: Session,
    *,
    owner_id: str,
    page_id: int,
    video: ReferenceVideo,
    analysis: dict,
) -> dict[str, int]:
    """Save observations and attach them to matching patterns within this Page only."""
    candidates = _extract_candidates(analysis)
    metrics = {
        "views": video.views_count,
        "reactions": video.reactions_count,
        "shares": video.shares_count,
        "comments": video.comments_count,
        "provenance": "user_supplied",
    }
    saved_elements = 0
    matched_patterns: set[int] = set()

    for raw in candidates[:100]:
        if not isinstance(raw, dict):
            continue
        element_type = _normalize(_text(raw.get("element_type") or raw.get("category") or "other")).replace(" ", "_")
        if element_type not in ALLOWED_TYPES:
            element_type = "other"
        name = _text(raw.get("name") or raw.get("pattern"), 180)
        description = _text(raw.get("description") or raw.get("observation"))
        construction = _text(raw.get("reusable_construction") or raw.get("technique") or raw.get("adaptation_idea"))
        if not name or not (description or construction):
            continue

        start = _number(raw.get("start_seconds", raw.get("timestamp_start")))
        end = _number(raw.get("end_seconds", raw.get("timestamp_end")))
        if start is not None and end is not None and end < start:
            start, end = end, start
        confidence = _confidence(raw.get("confidence"))
        triggers = raw.get("emotional_triggers", raw.get("emotional_trigger", []))
        if not isinstance(triggers, list):
            triggers = [triggers] if isinstance(triggers, str) else []

        element = CreativeElement(
            owner_id=owner_id,
            page_id=page_id,
            reference_video_id=video.id,
            element_type=element_type,
            name=name,
            description=description,
            start_seconds=start,
            end_seconds=end,
            observed_text=_text(raw.get("observed_text"), 2000),
            reusable_construction=construction,
            attributes={
                "emotional_triggers": [_text(x, 80) for x in triggers[:10] if isinstance(x, str)],
                "visual_evidence": _text(raw.get("observed_visual"), 1000),
                "audio_evidence": _text(raw.get("observed_audio"), 1000),
                "source_stage": _text(raw.get("stage"), 80),
            },
            confidence_score=confidence,
        )
        db.add(element)
        db.flush()
        saved_elements += 1

        normalized_name = _normalize(name)
        normalized_key = f"{element_type}:{normalized_name}"
        pattern = db.scalar(select(CreativePattern).where(
            CreativePattern.owner_id == owner_id,
            CreativePattern.page_id == page_id,
            CreativePattern.normalized_key == normalized_key,
        ))
        if pattern is None:
            # Conservative fuzzy matching; never cross Page, owner or category boundaries.
            existing = list(db.scalars(select(CreativePattern).where(
                CreativePattern.owner_id == owner_id,
                CreativePattern.page_id == page_id,
                CreativePattern.category == element_type,
                CreativePattern.status != "archived",
            )).all())
            best = max(existing, key=lambda p: SequenceMatcher(
                None, normalized_name, p.normalized_key.split(":", 1)[-1]
            ).ratio(), default=None)
            if best and SequenceMatcher(
                None, normalized_name, best.normalized_key.split(":", 1)[-1]
            ).ratio() >= 0.92:
                pattern = best

        if pattern is None:
            pattern = CreativePattern(
                owner_id=owner_id,
                page_id=page_id,
                category=element_type,
                name=name,
                normalized_key=normalized_key or f"{element_type}:element-{element.id}",
                description=description,
                reusable_construction=construction,
                occurrence_count=0,
                supporting_video_count=0,
                confidence_score=confidence,
                status="emerging",
            )
            db.add(pattern)
            db.flush()
        else:
            if len(description) > len(pattern.description or ""):
                pattern.description = description
            if construction and len(construction) > len(pattern.reusable_construction or ""):
                pattern.reusable_construction = construction

        prior_occurrences = pattern.occurrence_count
        db.add(PatternEvidence(
            pattern_id=pattern.id,
            creative_element_id=element.id,
            reference_video_id=video.id,
            evidence_description=description or construction,
            timestamp_start=start,
            timestamp_end=end,
            performance_context=metrics,
        ))
        pattern.occurrence_count = prior_occurrences + 1
        matched_patterns.add(pattern.id)
        pattern.last_observed_at = datetime.now(timezone.utc)
        if confidence is not None:
            previous = pattern.confidence_score
            pattern.confidence_score = confidence if previous is None else round(
                (previous * prior_occurrences + confidence) / (prior_occurrences + 1), 3
            )

    for pattern_id in matched_patterns:
        pattern = db.get(CreativePattern, pattern_id)
        if pattern is None:
            continue
        # Materialize the distinct source IDs explicitly. This is portable across
        # PostgreSQL and SQLite test databases and avoids dialect-specific aggregate
        # behavior affecting the maturity threshold.
        supporting_video_ids = set(db.scalars(
            select(PatternEvidence.reference_video_id).where(
                PatternEvidence.pattern_id == pattern_id
            ).distinct()
        ).all())
        count = len(supporting_video_ids)
        pattern.supporting_video_count = count
        # Repetition across distinct videos is a maturity label, not a performance claim.
        pattern.status = "active" if count >= 3 else "emerging"

    return {"elements_saved": saved_elements, "patterns_updated": len(matched_patterns)}
