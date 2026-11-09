from app.core.settings import settings


def _create_reference(client, page_name="Curious Science"):
    page = client.post("/api/v1/pages", json={"name": page_name}).json()
    reference = client.post(
        f"/api/v1/pages/{page['id']}/references",
        json={"source_url": "https://www.facebook.com/NASA", "display_name": "NASA"},
    ).json()
    return page, reference


def test_reference_posts_require_meta_access_configuration(client, monkeypatch):
    page, reference = _create_reference(client)
    monkeypatch.setattr(settings, "meta_access_token", None)
    response = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/collect"
    )
    assert response.status_code == 503
    assert "not configured yet" in response.json()["detail"]


def test_reference_post_endpoints_are_scoped_to_workspace(client):
    page, reference = _create_reference(client)
    other_page = client.post("/api/v1/pages", json={"name": "Wildlife"}).json()
    response = client.get(
        f"/api/v1/pages/{other_page['id']}/references/{reference['id']}/posts"
    )
    assert response.status_code == 404


def test_paused_reference_cannot_be_collected(client, monkeypatch):
    page, reference = _create_reference(client)
    client.patch(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}",
        json={"status": "paused"},
    )
    response = client.post(
        f"/api/v1/pages/{page['id']}/references/{reference['id']}/collect"
    )
    assert response.status_code == 409
