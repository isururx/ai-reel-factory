from unittest.mock import patch

from app.models.page import Page, PageProfile


def _seed(client, with_profile=True):
    from app.database.session import get_db

    db = next(client.app.dependency_overrides[get_db]())
    page = Page(name="Science", owner_id="test-user-0001")
    db.add(page)
    db.flush()
    if with_profile:
        db.add(PageProfile(page_id=page.id, niche="Science", target_audience="General audience"))
    db.commit()
    page_id = page.id
    db.close()
    return page_id


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


def test_generate_one_script_directly_from_brief(client):
    page_id = _seed(client)
    brief = "Explain an interesting science discovery for a general audience."
    with patch("app.api.routes.scripts.generate_script", return_value=_generated_script()) as generator:
        response = client.post(
            f"/api/v1/pages/{page_id}/scripts/generate",
            json={"brief": brief, "source_url": "https://example.com/source"},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version_number"] == 1
    assert body["status"] == "review"
    context = generator.call_args.args[0]
    assert context["brief"] == brief
    assert context["source_url"] == "https://example.com/source"


def test_generation_requires_page_profile(client):
    page_id = _seed(client, with_profile=False)
    response = client.post(
        f"/api/v1/pages/{page_id}/scripts/generate",
        json={"brief": "Create an interesting science explainer for a broad audience."},
    )
    assert response.status_code == 400
    assert "Page profile" in response.text


def test_generation_rejects_short_brief(client):
    page_id = _seed(client)
    response = client.post(
        f"/api/v1/pages/{page_id}/scripts/generate",
        json={"brief": "Too short"},
    )
    assert response.status_code == 422


def test_edit_creates_a_new_immutable_version(client):
    page_id = _seed(client)
    with patch("app.api.routes.scripts.generate_script", return_value=_generated_script()):
        generated = client.post(
            f"/api/v1/pages/{page_id}/scripts/generate",
            json={"brief": "Explain a fascinating science discovery to a general audience."},
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



def test_superseded_script_version_cannot_be_approved(client):
    page_id = _seed(client)
    with patch("app.api.routes.scripts.generate_script", return_value=_generated_script()):
        generated = client.post(
            f"/api/v1/pages/{page_id}/scripts/generate",
            json={"brief": "Explain a fascinating science discovery to a general audience."},
        ).json()

    original_version_id = generated["versions"][0]["id"]
    edited = client.post(
        f"/api/v1/pages/{page_id}/scripts/{generated['id']}/versions",
        json={
            "title": "Updated title",
            "hook": "A revised opening hook",
            "narration": "A revised narration for this science explainer.",
            "caption": "Updated caption.",
            "hashtags": ["#science"],
        },
    )
    assert edited.status_code == 201, edited.text

    response = client.post(
        f"/api/v1/pages/{page_id}/scripts/{generated['id']}/versions/{original_version_id}/decision",
        json={"decision": "approved", "comments": ""},
    )
    assert response.status_code == 409
    assert "latest saved script version" in response.text.lower()
