def create_page(client, name="Curious Science"):
    return client.post("/api/v1/pages", json={"name": name}).json()


def test_add_and_list_reference_page(client):
    page = create_page(client)
    created = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "https://www.facebook.com/NASA", "display_name": "NASA"},
    )
    assert created.status_code == 201
    assert created.json()["normalized_url"] == "https://www.facebook.com/NASA"
    listed = client.get(f"/api/v1/pages/{page['id']}/references")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["display_name"] == "NASA"


def test_reference_url_normalizes_tracking_and_mobile_hosts(client):
    page = create_page(client)
    response = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "https://m.facebook.com/NASA/?ref=bookmarks&utm_source=test"},
    )
    assert response.status_code == 201
    assert response.json()["normalized_url"] == "https://www.facebook.com/NASA"


def test_reference_rejects_non_facebook_and_non_page_urls(client):
    page = create_page(client)
    for url in [
        "https://example.com/nasa",
        "http://facebook.com/NASA",
        "https://www.facebook.com/watch/?v=123",
        "https://www.facebook.com/groups/science",
    ]:
        response = client.post(f"/api/v1/pages/{page['id']}/references", json={"source_url": url})
        assert response.status_code == 422


def test_duplicate_reference_is_rejected(client):
    page = create_page(client)
    url = f"/api/v1/pages/{page['id']}/references"
    assert client.post(url, json={"source_url": "facebook.com/NASA"}).status_code == 201
    duplicate = client.post(url, json={"source_url": "https://m.facebook.com/NASA/?ref=home"})
    assert duplicate.status_code == 409


def test_reference_can_be_paused_and_deleted(client):
    page = create_page(client)
    created = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "facebook.com/NASA"},
    ).json()
    updated = client.patch(
        f"/api/v1/pages/{page['id']}/references/{created['id']}",
        json={"status": "paused", "notes": "Watch educational video formats."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "paused"
    assert updated.json()["notes"] == "Watch educational video formats."
    deleted = client.delete(f"/api/v1/pages/{page['id']}/references/{created['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/pages/{page['id']}/references").json() == []


def test_reference_registry_is_scoped_to_owned_page(client):
    page = create_page(client)
    other_page = create_page(client, "Wildlife")
    created = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "facebook.com/NASA"},
    ).json()
    assert client.get(f"/api/v1/pages/{other_page['id']}/references").json() == []
    assert client.patch(
        f"/api/v1/pages/{other_page['id']}/references/{created['id']}",
        json={"status": "paused"},
    ).status_code == 404
