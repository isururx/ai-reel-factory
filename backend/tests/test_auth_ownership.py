from app.core.auth import AuthenticatedUser, get_current_user
from app.main import app


def test_page_is_hidden_from_a_different_authenticated_user(client):
    created = client.post("/api/v1/pages", json={"name": "Private science page"})
    assert created.status_code == 201
    page_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser("another-user-0002")
    response = client.get(f"/api/v1/pages/{page_id}")
    assert response.status_code == 404
    assert client.get("/api/v1/pages").json() == []


def test_page_api_rejects_requests_without_a_bearer_token(client):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/api/v1/pages")
    assert response.status_code == 401
