from unittest.mock import patch

from app.models.creative_intelligence import CreativePattern
from app.models.page import Page, PageProfile
from app.models.production_pipeline import ScriptBatch
from app.models.strategy import PageStrategy, StrategyVersion


def _seed_batch_context(client, db_session):
    page = Page(name="Science", owner_id="test-user-0001")
    db_session.add(page)
    db_session.flush()
    db_session.add(PageProfile(
        page_id=page.id,
        niche="Science",
        target_audience="General audience",
        language="English",
        tone={"style": "curious"},
    ))
    strategy = PageStrategy(
        page_id=page.id,
        name="Curiosity-led explainers",
        description="Short science explainers",
        status="active",
    )
    db_session.add(strategy)
    db_session.flush()
    version = StrategyVersion(
        strategy_id=strategy.id,
        version_number=1,
        configuration={"format": "curiosity explainer"},
        status="active",
    )
    db_session.add(version)
    pattern = CreativePattern(
        owner_id="test-user-0001",
        page_id=page.id,
        category="hook",
        name="Unexpected question",
        normalized_key="unexpected-question",
        description="Open with a surprising question",
        reusable_construction="Ask a specific question that challenges an assumption",
        status="active",
        supporting_video_count=4,
        occurrence_count=6,
    )
    db_session.add(pattern)
    db_session.commit()
    return page.id, strategy.id, version.id, pattern.id


def test_create_automatic_script_batch_uses_strategy_and_patterns(client, db_session):
    page_id, strategy_id, version_id, pattern_id = _seed_batch_context(client, db_session)
    with patch("app.api.routes.script_batches.generate_script_batch.delay") as enqueue:
        response = client.post(
            f"/api/v1/pages/{page_id}/script-batches",
            json={
                "strategy_id": strategy_id,
                "strategy_version_id": version_id,
                "mode": "automatic",
                "pattern_selection": "automatic",
                "script_count": 3,
            },
        )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["requested_count"] == 3
    assert body["status"] == "queued"
    enqueue.assert_called_once_with(body["id"])

    batch = db_session.get(ScriptBatch, body["id"])
    assert batch.input_snapshot["strategy"] == {"format": "curiosity explainer"}
    assert pattern_id in batch.input_snapshot["creative_pattern_ids"]
    assert "science" in batch.input_snapshot["brief"].lower()


def test_manual_batch_requires_a_brief(client, db_session):
    page_id, strategy_id, version_id, _ = _seed_batch_context(client, db_session)
    response = client.post(
        f"/api/v1/pages/{page_id}/script-batches",
        json={
            "strategy_id": strategy_id,
            "strategy_version_id": version_id,
            "mode": "manual",
            "pattern_selection": "automatic",
            "script_count": 2,
        },
    )
    assert response.status_code == 422
    assert "manual batch requires" in response.text.lower()


def test_batch_rejects_strategy_version_from_another_strategy(client, db_session):
    page_id, strategy_id, version_id, _ = _seed_batch_context(client, db_session)
    other = PageStrategy(page_id=page_id, name="Other strategy", description="")
    db_session.add(other)
    db_session.flush()
    other_version = StrategyVersion(strategy_id=other.id, version_number=1, configuration={})
    db_session.add(other_version)
    db_session.commit()

    response = client.post(
        f"/api/v1/pages/{page_id}/script-batches",
        json={
            "strategy_id": strategy_id,
            "strategy_version_id": other_version.id,
            "mode": "manual",
            "brief": "Create a surprising science explainer for curious viewers.",
            "pattern_selection": "automatic",
            "script_count": 1,
        },
    )
    assert response.status_code == 404
