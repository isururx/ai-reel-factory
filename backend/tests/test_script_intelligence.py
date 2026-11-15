from app.models.creative_intelligence import CreativeElement, CreativePattern, PatternEvidence
from app.models.page import Page
from app.models.reference_video import ReferenceVideo
from app.services.script_intelligence import build_script_intelligence_context


def _pattern(db, page_id: int, *, owner_id: str = "test-user-0001", status: str = "active", name: str = "Curiosity gap"):
    pattern = CreativePattern(
        owner_id=owner_id,
        page_id=page_id,
        category="hook",
        name=name,
        normalized_key=f"hook:{name.lower().replace(' ', '-')}",
        description="Open with an unusual event and delay the explanation.",
        reusable_construction="Introduce a surprising observation, then reveal the explanation in stages.",
        occurrence_count=5,
        supporting_video_count=3,
        confidence_score=0.9,
        status=status,
    )
    db.add(pattern)
    db.flush()
    return pattern


def test_script_intelligence_is_page_scoped_and_uses_active_patterns(db_session):
    first_page = Page(name="Mystery", owner_id="test-user-0001")
    second_page = Page(name="Science", owner_id="test-user-0001")
    db_session.add_all([first_page, second_page])
    db_session.flush()

    active = _pattern(db_session, first_page.id)
    _pattern(db_session, first_page.id, status="emerging", name="Emerging pattern")
    _pattern(db_session, second_page.id, name="Other page pattern")
    db_session.commit()

    context = build_script_intelligence_context(
        db_session,
        owner_id="test-user-0001",
        page_id=first_page.id,
        trend_title="An unexplained discovery",
        trend_summary="Scientists investigate a mysterious event.",
        niche="Mystery",
        target_audience="General audience",
    )

    assert [item["pattern_id"] for item in context["patterns"]] == [active.id]
    assert context["provenance"]["patterns_available"] == 1
    assert context["provenance"]["patterns_used"][0]["name"] == "Curiosity gap"


def test_script_intelligence_includes_compact_traceable_evidence(db_session):
    page = Page(name="Mystery", owner_id="test-user-0001")
    db_session.add(page)
    db_session.flush()

    video = ReferenceVideo(
        owner_id="test-user-0001",
        page_id=page.id,
        reference_page_id=None,
        reference_post_id=None,
        title="Reference clip",
        source_url="https://example.com/reference",
        object_key=f"reference-videos/test/{page.id}/clip.mp4",
        original_filename="clip.mp4",
        content_type="video/mp4",
        file_size=1024,
        manual_comments=[],
        analysis_status="completed",
        analysis_result={},
    )
    db_session.add(video)
    db_session.flush()

    element = CreativeElement(
        owner_id="test-user-0001",
        page_id=page.id,
        reference_video_id=video.id,
        element_type="hook",
        name="Curiosity gap",
        description="The cause is withheld until later.",
        reusable_construction="Reveal the explanation in stages.",
        observed_text="",
        attributes={},
        confidence_score=0.9,
    )
    db_session.add(element)
    db_session.flush()
    pattern = _pattern(db_session, page.id)
    db_session.add(PatternEvidence(
        pattern_id=pattern.id,
        creative_element_id=element.id,
        reference_video_id=video.id,
        evidence_description="The opening raises a question and delays the answer.",
        timestamp_start=0.0,
        timestamp_end=5.0,
        performance_context={"provenance": "user_supplied"},
    ))
    db_session.commit()

    context = build_script_intelligence_context(
        db_session,
        owner_id="test-user-0001",
        page_id=page.id,
        trend_title="An unexplained discovery",
        trend_summary="A mystery story.",
        niche="Mystery",
        target_audience="General audience",
    )

    evidence = context["patterns"][0]["evidence_examples"]
    assert len(evidence) == 1
    assert evidence[0]["reference_video_id"] == video.id
    assert evidence[0]["timestamp_start"] == 0.0
