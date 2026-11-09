def test_reference_video_submission_enters_fifo_queue(client, monkeypatch):
    from app.api.routes import reference_video_queue

    dispatched = []
    monkeypatch.setattr(
        reference_video_queue.drain_next_reference_video_job,
        "delay",
        lambda: dispatched.append("drain"),
    )
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()

    first = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={
            "source_url": "https://www.facebook.com/reel/123456",
            "views_count": 12000,
            "reactions_count": 850,
            "shares_count": 40,
            "comments_count": 70,
            "manual_comments": ["Great explanation", "Part two please"],
            "engagement_notes": "Observed manually for testing.",
        },
    )
    second = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={"source_url": "https://www.facebook.com/reel/789012"},
    )

    assert first.status_code == 202, first.text
    assert second.status_code == 202, second.text
    assert first.json()["status"] == "queued"
    assert first.json()["queue_position"] == 1
    assert second.json()["queue_position"] == 2
    assert first.json()["views_count"] == 12000
    assert first.json()["reactions_count"] == 850
    assert len(dispatched) == 2

    queue = client.get(f"/api/v1/pages/{page['id']}/reference-videos/queue")
    assert queue.status_code == 200
    assert queue.json()["queued_count"] == 2
    assert [job["id"] for job in queue.json()["jobs"]] == [
        second.json()["id"], first.json()["id"]
    ]


def test_reference_video_queue_rejects_non_facebook_urls(client):
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    response = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={"source_url": "https://example.com/video.mp4"},
    )
    assert response.status_code == 422


def test_reference_video_queue_is_page_owner_scoped(client, monkeypatch):
    from app.api.routes import reference_video_queue

    monkeypatch.setattr(reference_video_queue.drain_next_reference_video_job, "delay", lambda: None)
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    queued = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={"source_url": "https://www.facebook.com/reel/123456"},
    )
    assert queued.status_code == 202

    other_page = client.post("/api/v1/pages", json={"name": "Wildlife"}).json()
    response = client.get(f"/api/v1/pages/{other_page['id']}/reference-videos/queue")
    assert response.status_code == 200
    assert response.json()["jobs"] == []
