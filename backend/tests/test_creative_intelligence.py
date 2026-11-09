from app.models.creative_intelligence import CreativePattern
from app.models.reference_video import ReferenceVideo
from app.services.creative_intelligence import persist_creative_intelligence


def _video(db_session, page_id: int, title: str) -> ReferenceVideo:
    video = ReferenceVideo(
        owner_id="test-user-0001",
        page_id=page_id,
        reference_page_id=None,
        reference_post_id=None,
        title=title,
        source_url="https://www.facebook.com/reel/example",
        object_key=f"reference-videos/test/{page_id}/{title.replace(' ', '-')}.mp4",
        original_filename="example.mp4",
        content_type="video/mp4",
        file_size=1024,
        views_count=12000,
        reactions_count=500,
        shares_count=40,
        comments_count=60,
        manual_comments=[],
        engagement_notes="Entered manually",
        analysis_status="completed",
        analysis_result={},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


def _analysis():
    return {
        "creative_elements": [
            {
                "element_type": "hook",
                "name": "Unexplained Event Curiosity Gap",
                "description": "Opens with an unexplained event and delays the cause.",
                "start_seconds": 0,
                "end_seconds": 4.5,
                "observed_text": "Nobody knew what happened",
                "reusable_construction": "Introduce an unusual event, then delay the explanation.",
                "confidence": "high",
            }
        ]
    }


def test_patterns_accumulate_evidence_and_activate_after_three_videos(client, db_session):
    page = client.post("/api/v1/pages", json={"name": "Mystery"}).json()
    page_id = page["id"]

    for index in range(3):
        video = _video(db_session, page_id, f"Reference {index}")
        result = persist_creative_intelligence(
            db_session,
            owner_id="test-user-0001",
            page_id=page_id,
            video=video,
            analysis=_analysis(),
        )
        db_session.commit()
        assert result["elements_saved"] == 1
        assert result["patterns_updated"] == 1

    pattern = db_session.query(CreativePattern).filter_by(page_id=page_id).one()
    assert pattern.supporting_video_count == 3
    assert pattern.occurrence_count == 3
    assert pattern.status == "active"

    response = client.get(f"/api/v1/pages/{page_id}/creative-intelligence/patterns")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Unexplained Event Curiosity Gap"


def test_patterns_are_isolated_between_pages(client, db_session):
    first = client.post("/api/v1/pages", json={"name": "Mystery"}).json()
    second = client.post("/api/v1/pages", json={"name": "Science"}).json()
    video = _video(db_session, first["id"], "Mystery reference")
    persist_creative_intelligence(
        db_session,
        owner_id="test-user-0001",
        page_id=first["id"],
        video=video,
        analysis=_analysis(),
    )
    db_session.commit()

    first_patterns = client.get(f"/api/v1/pages/{first['id']}/creative-intelligence/patterns")
    second_patterns = client.get(f"/api/v1/pages/{second['id']}/creative-intelligence/patterns")
    assert first_patterns.status_code == 200
    assert len(first_patterns.json()) == 1
    assert second_patterns.status_code == 200
    assert second_patterns.json() == []


def test_invalid_or_empty_elements_are_not_saved(client, db_session):
    page = client.post("/api/v1/pages", json={"name": "Science"}).json()
    video = _video(db_session, page["id"], "Science reference")
    result = persist_creative_intelligence(
        db_session,
        owner_id="test-user-0001",
        page_id=page["id"],
        video=video,
        analysis={"creative_elements": [
            {"element_type": "unknown", "name": "", "description": ""},
            {"element_type": "visual", "name": "Visual contrast", "description": "A visible contrast.", "confidence": 0.8},
        ]},
    )
    db_session.commit()
    assert result["elements_saved"] == 1
