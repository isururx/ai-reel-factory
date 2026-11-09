def _create_reference(client):
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    reference = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "https://www.facebook.com/NASA", "display_name": "NASA"},
    ).json()
    return page, reference


def test_upload_reference_video_stores_manual_metrics_and_comments(client, monkeypatch):
    from app.api.routes import reference_videos

    page, reference = _create_reference(client)
    monkeypatch.setattr(reference_videos, "upload_fileobj", lambda fileobj, key, content_type: key)
    response = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/videos",
        files={"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
        data={
            "title": "Test reference clip",
            "views_count": "12000",
            "reactions_count": "840",
            "shares_count": "35",
            "comments_count": "62",
            "manual_comments_json": '["Amazing explanation", "Please make part two"]',
            "engagement_notes": "Counts manually observed for testing.",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["title"] == "Test reference clip"
    assert payload["views_count"] == 12000
    assert payload["reactions_count"] == 840
    assert payload["shares_count"] == 35
    assert payload["comments_count"] == 62
    assert payload["manual_comments"] == ["Amazing explanation", "Please make part two"]
    assert payload["analysis_status"] == "pending"

    listed = client.get(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/videos"
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_reference_video_cannot_be_read_from_another_workspace(client, monkeypatch):
    from app.api.routes import reference_videos

    page, reference = _create_reference(client)
    monkeypatch.setattr(reference_videos, "upload_fileobj", lambda fileobj, key, content_type: key)
    uploaded = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/videos",
        files={"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
    )
    assert uploaded.status_code == 201

    other_page = client.post("/api/v1/pages", json={"name": "Wildlife"}).json()
    response = client.get(
        f"/api/v1/pages/{other_page['id']}/references/{reference['id']}/videos"
    )
    assert response.status_code == 404


def test_reference_video_analysis_saves_page_scoped_insight(client, monkeypatch):
    from app.api.routes import reference_videos

    page, reference = _create_reference(client)
    monkeypatch.setattr(reference_videos, "upload_fileobj", lambda fileobj, key, content_type: key)

    uploaded = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/videos",
        files={"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    video_id = uploaded.json()["id"]

    def fake_download(object_key, destination):
        from pathlib import Path
        Path(destination).write_bytes(b"fake-video-bytes")

    expected = {
        "summary": "A short science explainer.",
        "hook": {"description": "A surprising opening question", "strength": "high"},
        "reusable_patterns": [
            {"pattern": "Question-led hook", "adaptation_idea": "Create an original question"}
        ],
    }
    monkeypatch.setattr(reference_videos, "download_file", fake_download)
    monkeypatch.setattr(reference_videos, "analyze_video_file", lambda path, context: expected)

    analyzed = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/videos/{video_id}/analyze"
    )
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["analysis_status"] == "completed"
    assert analyzed.json()["analysis_result"]["summary"] == expected["summary"]

    insights = client.get(f"/api/v1/pages/{page['id']}/reference-insights")
    assert insights.status_code == 200
    assert len(insights.json()) == 1
    insight = insights.json()[0]
    assert insight["review_status"] == "pending_review"
    assert insight["content"]["summary"] == expected["summary"]

    reviewed = client.patch(
        f"/api/v1/pages/{page['id']}/reference-insights/{insight['id']}/review",
        json={"review_status": "approved", "reviewer_notes": "Useful pattern."},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_status"] == "approved"
