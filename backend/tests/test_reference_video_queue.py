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


def test_reference_video_queue_accepts_manual_primary_model(client, monkeypatch):
    from app.api.routes import reference_video_queue

    monkeypatch.setattr(reference_video_queue.drain_next_reference_video_job, "delay", lambda: None)
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    response = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={
            "source_url": "https://www.facebook.com/reel/123456",
            "analysis_primary_provider": "gemini",
            "analysis_primary_model": "gemini-2.5-flash",
        },
    )
    assert response.status_code == 202, response.text
    assert response.json()["analysis_primary_provider"] == "gemini"
    assert response.json()["analysis_primary_model"] == "gemini-2.5-flash"


def test_reference_video_queue_rejects_unsupported_manual_model(client, monkeypatch):
    from app.api.routes import reference_video_queue

    monkeypatch.setattr(reference_video_queue.drain_next_reference_video_job, "delay", lambda: None)
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    response = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={
            "source_url": "https://www.facebook.com/reel/123456",
            "analysis_primary_provider": "gemini",
            "analysis_primary_model": "unsupported-model",
        },
    )
    assert response.status_code == 422


def test_reference_video_queue_rejects_non_facebook_urls(client):
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    response = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={"source_url": "https://example.com/video.mp4"},
    )
    assert response.status_code == 422


def test_failed_reference_video_job_can_be_retried(client, db_session, monkeypatch):
    from app.api.routes import reference_video_queue
    from app.models.reference_video_job import ReferenceVideoJob

    dispatched = []
    monkeypatch.setattr(
        reference_video_queue.drain_next_reference_video_job,
        "delay",
        lambda: dispatched.append("drain"),
    )
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    queued = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={
            "source_url": "https://www.facebook.com/reel/123456",
            "views_count": 12000,
            "reactions_count": 850,
            "shares_count": 40,
            "comments_count": 70,
            "manual_comments": ["Great explanation"],
            "engagement_notes": "Observed manually.",
        },
    )
    assert queued.status_code == 202
    job = db_session.get(ReferenceVideoJob, queued.json()["id"])
    job.status = "failed"
    job.error_message = "Gemini temporarily unavailable (503)."
    db_session.commit()

    retried = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue/{job.id}/retry"
    )
    assert retried.status_code == 202, retried.text
    payload = retried.json()
    assert payload["status"] == "queued"
    assert payload["error_message"] is None
    assert payload["views_count"] == 12000
    assert payload["reactions_count"] == 850
    assert payload["shares_count"] == 40
    assert payload["comments_count"] == 70
    assert len(dispatched) == 2


def test_only_failed_reference_video_jobs_can_be_retried(client, monkeypatch):
    from app.api.routes import reference_video_queue

    monkeypatch.setattr(reference_video_queue.drain_next_reference_video_job, "delay", lambda: None)
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    queued = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={"source_url": "https://www.facebook.com/reel/123456"},
    )
    response = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue/{queued.json()['id']}/retry"
    )
    assert response.status_code == 409


def test_analysis_attempt_history_is_page_owner_scoped(client, db_session):
    from datetime import datetime, timezone
    from app.models.reference_video import ReferenceVideo
    from app.models.reference_video_analysis_attempt import ReferenceVideoAnalysisAttempt

    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    video = ReferenceVideo(
        owner_id="test-user-0001", page_id=page["id"], reference_page_id=None,
        reference_post_id=None, title="Test video", source_url="https://www.facebook.com/reel/123456",
        object_key="reference-videos/test/attempt-log.mp4", original_filename="clip.mp4",
        content_type="video/mp4", file_size=100, manual_comments=[], engagement_notes="",
        analysis_status="completed", analysis_result={"summary": "Test"},
        analysis_provider="gemini", analysis_model="gemini-2.5-flash",
        analysis_attempt_count=2, analysis_total_duration_ms=12000,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    db_session.add_all([
        ReferenceVideoAnalysisAttempt(
            owner_id="test-user-0001", page_id=page["id"], reference_video_id=video.id,
            attempt_number=1, provider="gemini", model_id="gemini-3.5-flash-lite",
            status="failed", error_code="503", error_message="Unavailable", duration_ms=2000,
            started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
        ),
        ReferenceVideoAnalysisAttempt(
            owner_id="test-user-0001", page_id=page["id"], reference_video_id=video.id,
            attempt_number=2, provider="gemini", model_id="gemini-2.5-flash",
            status="completed", duration_ms=10000, input_tokens=100, output_tokens=50,
            started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
        ),
    ])
    db_session.commit()

    response = client.get(
        f"/api/v1/pages/{page['id']}/reference-videos/{video.id}/analysis-attempts"
    )
    assert response.status_code == 200
    assert [item["model_id"] for item in response.json()] == [
        "gemini-3.5-flash-lite", "gemini-2.5-flash"
    ]
    assert response.json()[0]["status"] == "failed"
    assert response.json()[1]["status"] == "completed"


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


def test_login_restricted_job_can_resume_with_manual_upload(client, db_session, monkeypatch):
    from app.api.routes import reference_video_queue

    monkeypatch.setattr(reference_video_queue.drain_next_reference_video_job, "delay", lambda: None)
    monkeypatch.setattr(reference_video_queue, "upload_fileobj", lambda *args, **kwargs: "stored-key")
    page = client.post("/api/v1/pages", json={"name": "Curious Science"}).json()
    queued = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue",
        json={
            "source_url": "https://www.facebook.com/reel/123456",
            "title": "Dog begs for Food",
            "views_count": 25000,
            "reactions_count": 900,
            "manual_comments": ["Cute dog!", "So funny"],
        },
    )
    assert queued.status_code == 202
    job_id = queued.json()["id"]

    # Simulate the worker pausing a Facebook URL that cannot be accessed without login.
    from app.models.reference_video_job import ReferenceVideoJob
    job = db_session.get(ReferenceVideoJob, job_id)
    job.status = "needs_upload"
    job.error_message = "Facebook requires login."
    db_session.commit()

    uploaded = client.post(
        f"/api/v1/pages/{page['id']}/reference-videos/queue/{job_id}/upload",
        files={"file": ("replacement.mp4", b"fake-video-bytes", "video/mp4")},
    )
    assert uploaded.status_code == 202, uploaded.text
    payload = uploaded.json()
    assert payload["status"] == "queued"
    assert payload["source_url"] == "https://www.facebook.com/reel/123456"
    assert payload["views_count"] == 25000
    assert payload["reactions_count"] == 900
