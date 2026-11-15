from unittest.mock import patch

from sqlalchemy import select

from app.models.page import Page, PageProfile
from app.models.production_pipeline import VideoProductionJob
from app.services.video_generation.base import VideoRenderRequest
from app.services.video_generation.mock import MockVideoProvider


def _seed_page(client):
    from app.database.session import get_db

    db = next(client.app.dependency_overrides[get_db]())
    page = Page(name="Science", owner_id="test-user-0001")
    db.add(page)
    db.flush()
    db.add(PageProfile(page_id=page.id, niche="Science", target_audience="General audience"))
    db.commit()
    page_id = page.id
    db.close()
    return page_id


def _create_script(client, page_id):
    with patch("app.api.routes.scripts.generate_script", return_value={
        "title": "A science story",
        "hook": "Here is a surprising discovery.",
        "narration": "A complete narration for a short science video.",
        "caption": "Discover the science.",
        "hashtags": ["#science"],
        "script_data": {"estimated_duration_seconds": 65},
    }):
        response = client.post(
            f"/api/v1/pages/{page_id}/scripts/generate",
            json={"brief": "Explain an interesting science discovery to a general audience."},
        )
    assert response.status_code == 201, response.text
    return response.json()


def test_approval_creates_one_queued_video_job_and_dispatches(client):
    from app.database.session import get_db

    page_id = _seed_page(client)
    script = _create_script(client, page_id)
    version_id = script["versions"][0]["id"]

    with patch("app.api.routes.scripts.render_video_job.delay") as dispatch:
        response = client.post(
            f"/api/v1/pages/{page_id}/scripts/{script['id']}/versions/{version_id}/decision",
            json={"decision": "approved", "comments": "Looks good."},
        )
        assert response.status_code == 200, response.text
        dispatch.assert_called_once()
        job_id = dispatch.call_args.args[0]

        repeated = client.post(
            f"/api/v1/pages/{page_id}/scripts/{script['id']}/versions/{version_id}/decision",
            json={"decision": "approved", "comments": "Approved again."},
        )
        assert repeated.status_code == 200, repeated.text
        assert dispatch.call_count == 1

    db = next(client.app.dependency_overrides[get_db]())
    jobs = db.scalars(select(VideoProductionJob).where(
        VideoProductionJob.script_version_id == version_id
    )).all()
    assert len(jobs) == 1
    assert jobs[0].id == job_id
    assert jobs[0].status == "queued"
    assert jobs[0].provider == "mock"
    db.close()


def test_rejected_script_does_not_create_video_job(client):
    from app.database.session import get_db

    page_id = _seed_page(client)
    script = _create_script(client, page_id)
    version_id = script["versions"][0]["id"]
    with patch("app.api.routes.scripts.render_video_job.delay") as dispatch:
        response = client.post(
            f"/api/v1/pages/{page_id}/scripts/{script['id']}/versions/{version_id}/decision",
            json={"decision": "rejected", "comments": "Needs revision."},
        )
    assert response.status_code == 200, response.text
    dispatch.assert_not_called()
    db = next(client.app.dependency_overrides[get_db]())
    assert db.scalar(select(VideoProductionJob).where(
        VideoProductionJob.script_version_id == version_id
    )) is None
    db.close()


def test_mock_provider_returns_explicit_simulation_metadata():
    request = VideoRenderRequest(
        job_id=1, owner_id="owner-1", page_id=2, script_id=3,
        script_version_id=4, title="Test Reel", hook="A hook",
        narration="A narration", caption="A caption", hashtags=["#test"],
        script_data={"estimated_duration_seconds": 60},
    )
    result = MockVideoProvider().render(request)
    assert result.provider_job_id.startswith("mock-")
    assert result.output_object_key.startswith("mock://")
    assert result.metadata["simulation"] is True
    assert result.metadata["artifact_created"] is False
