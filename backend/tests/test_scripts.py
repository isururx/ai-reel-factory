from unittest.mock import patch

from app.models.page import Page, PageProfile
from app.models.trend import PageTrendRecommendation, TrendItem


def _seed(client):
    from app.database.session import get_db

    db = next(client.app.dependency_overrides[get_db]())
    page = Page(name="Science", owner_id="test-user-0001")
    db.add(page)
    db.flush()
    db.add(PageProfile(page_id=page.id, niche="Science", target_audience="General audience"))
    trend = TrendItem(
        owner_id="test-user-0001",
        source_name="Test",
        source_url="https://example.com/story",
        title="A science discovery",
        summary="A source summary",
    )
    db.add(trend)
    db.flush()
    recommendation = PageTrendRecommendation(page_id=page.id, trend_id=trend.id, status="selected")
    db.add(recommendation)
    db.commit()
    result = (page.id, recommendation.id)
    db.close()
    return result


def _generated_script():
    return {
        "title": "The surprising science discovery",
        "hook": "What if the world around you is not quite what you think?",
        "narration": "A complete narration about the discovery.",
        "caption": "A short caption.",
        "hashtags": ["#science"],
        "script_data": {
            "estimated_duration_seconds": 70,
            "evaluation": {
                "hook_score": 8,
                "storytelling_score": 8,
                "originality_score": 8,
                "visual_suitability_score": 8,
                "fact_check_notes": "Verify the original research.",
                "strengths": "Clear and visual storytelling.",
            },
        },
    }


def test_generate_one_finalized_script_for_review(client):
    page_id, recommendation_id = _seed(client)
    with patch("app.api.routes.scripts.generate_script", return_value=_generated_script()) as generator:
        response = client.post(
            f"/api/v1/pages/{page_id}/trends/{recommendation_id}/generate-scripts"
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version_number"] == 1
    assert body["status"] == "review"
    generator.assert_called_once()


def test_cannot_generate_for_unselected_trend(client):
    page_id, recommendation_id = _seed(client)
    from app.database.session import get_db

    db = next(client.app.dependency_overrides[get_db]())
    db.get(PageTrendRecommendation, recommendation_id).status = "saved"
    db.commit()
    db.close()

    response = client.post(f"/api/v1/pages/{page_id}/trends/{recommendation_id}/generate-scripts")
    assert response.status_code == 404


def test_edit_creates_a_new_immutable_version(client):
    page_id, recommendation_id = _seed(client)
    with patch("app.api.routes.scripts.generate_script", return_value=_generated_script()):
        generated = client.post(
            f"/api/v1/pages/{page_id}/trends/{recommendation_id}/generate-scripts"
        ).json()

    response = client.post(
        f"/api/v1/pages/{page_id}/scripts/{generated['id']}/versions",
        json={
            "title": "Human edited title",
            "hook": "A better opening hook",
            "narration": "Human-edited narration.",
            "caption": "Edited caption.",
            "hashtags": ["#science"],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["version_number"] == 2
