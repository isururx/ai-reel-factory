def test_create_and_list_pages(client):
    created = client.post("/api/v1/pages", json={"name": "Science Daily"})
    assert created.status_code == 201 and created.json()["name"] == "Science Daily"
    listed = client.get("/api/v1/pages")
    assert listed.status_code == 200 and [p["name"] for p in listed.json()] == ["Science Daily"]

def test_profile_is_scoped_to_its_page(client):
    science = client.post("/api/v1/pages", json={"name": "Science"}).json()
    parenting = client.post("/api/v1/pages", json={"name": "Parenting"}).json()
    saved = client.put(f"/api/v1/pages/{science['id']}/profile", json={"niche": "science", "target_audience": "Curious adults"})
    assert saved.status_code == 200 and saved.json()["page_id"] == science["id"]
    assert client.get(f"/api/v1/pages/{parenting['id']}/profile").status_code == 404

def test_profile_upsert_updates_existing_record(client):
    page = client.post("/api/v1/pages", json={"name": "History"}).json()
    url = f"/api/v1/pages/{page['id']}/profile"
    first = client.put(url, json={"niche": "history"})
    second = client.put(url, json={"niche": "world history"})
    assert first.json()["id"] == second.json()["id"] and second.json()["niche"] == "world history"

def test_strategy_versions_are_page_scoped(client):
    science = client.post("/api/v1/pages", json={"name": "Science"}).json()
    wildlife = client.post("/api/v1/pages", json={"name": "Wildlife"}).json()
    created = client.post(f"/api/v1/pages/{science['id']}/strategies", json={"name": "Explainers", "configuration": {"hook_style": "question"}})
    assert created.status_code == 201
    sid = created.json()["id"]
    versions = client.get(f"/api/v1/pages/{science['id']}/strategies/{sid}/versions")
    assert versions.status_code == 200 and versions.json()[0]["version_number"] == 1
    assert client.get(f"/api/v1/pages/{wildlife['id']}/strategies/{sid}/versions").status_code == 404
