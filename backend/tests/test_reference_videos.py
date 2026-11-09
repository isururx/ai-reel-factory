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
