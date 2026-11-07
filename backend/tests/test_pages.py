def test_create_and_list_pages(client):
    created = client.post("/api/v1/pages", json={"name": "Science Daily"})
    assert created.status_code == 201 and created.json()["name"] == "Science Daily"
    listed = client.get("/api/v1/pages")
    assert listed.status_code == 200 and [p["name"] for p in listed.json()] == ["Science Daily"]


def test_page_can_be_updated_and_deactivated(client):
    page = client.post("/api/v1/pages", json={"name": "Science Daily"}).json()
    updated = client.patch(
        f"/api/v1/pages/{page['id']}",
        json={"name": "Science Explained", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Science Explained"
    assert updated.json()["is_active"] is False


def test_page_update_rejects_empty_payload(client):
    page = client.post("/api/v1/pages", json={"name": "Science"}).json()
    response = client.patch(f"/api/v1/pages/{page['id']}", json={})
    assert response.status_code == 422


def test_page_delete_cascades_page_owned_data(client):
    page = client.post("/api/v1/pages", json={"name": "History"}).json()
    page_id = page["id"]
    profile = client.put(
        f"/api/v1/pages/{page_id}/profile",
        json={"niche": "history"},
    )
    assert profile.status_code == 200

    deleted = client.delete(f"/api/v1/pages/{page_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/pages/{page_id}").status_code == 404


def test_profile_is_scoped_to_its_page(client):
    science = client.post("/api/v1/pages", json={"name": "Science"}).json()
    parenting = client.post("/api/v1/pages", json={"name": "Parenting"}).json()
    saved = client.put(
        f"/api/v1/pages/{science['id']}/profile",
        json={"niche": "science", "target_audience": "Curious adults"},
    )
    assert saved.status_code == 200 and saved.json()["page_id"] == science["id"]
    assert client.get(f"/api/v1/pages/{parenting['id']}/profile").status_code == 404


def test_profile_upsert_updates_existing_record(client):
    page = client.post("/api/v1/pages", json={"name": "History"}).json()
    url = f"/api/v1/pages/{page['id']}/profile"
    first = client.put(url, json={"niche": "history"})
    second = client.put(url, json={"niche": "world history"})
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["niche"] == "world history"


def test_strategy_versions_are_page_scoped_and_append_only(client):
    science = client.post("/api/v1/pages", json={"name": "Science"}).json()
    wildlife = client.post("/api/v1/pages", json={"name": "Wildlife"}).json()
    created = client.post(
        f"/api/v1/pages/{science['id']}/strategies",
        json={"name": "Explainers", "configuration": {"hook_style": "question"}},
    )
    assert created.status_code == 201
    strategy_id = created.json()["id"]

    first_versions = client.get(
        f"/api/v1/pages/{science['id']}/strategies/{strategy_id}/versions"
    )
    assert first_versions.status_code == 200
    assert first_versions.json()[0]["version_number"] == 1

    next_version = client.post(
        f"/api/v1/pages/{science['id']}/strategies/{strategy_id}/versions",
        json={"configuration": {"hook_style": "surprising_fact"}},
    )
    assert next_version.status_code == 201
    assert next_version.json()["version_number"] == 2
    assert next_version.json()["status"] == "draft"

    wrong_page = client.get(
        f"/api/v1/pages/{wildlife['id']}/strategies/{strategy_id}/versions"
    )
    assert wrong_page.status_code == 404


def test_strategy_can_be_paused(client):
    page = client.post("/api/v1/pages", json={"name": "Motivation"}).json()
    strategy = client.post(
        f"/api/v1/pages/{page['id']}/strategies",
        json={"name": "Daily inspiration"},
    ).json()
    updated = client.patch(
        f"/api/v1/pages/{page['id']}/strategies/{strategy['id']}",
        json={"status": "paused"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "paused"
