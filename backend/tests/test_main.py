from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Patch Redis cache helpers so tests don't need a live Redis instance
_cache_store: dict = {}


async def _mock_cache_get(key: str):
    return _cache_store.get(key)


async def _mock_cache_set(key: str, value: str, ttl=None):
    _cache_store[key] = value


async def _mock_cache_delete(key: str):
    _cache_store.pop(key, None)


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    import app.api.routes as routes_mod

    monkeypatch.setattr(routes_mod, "cache_get", _mock_cache_get)
    monkeypatch.setattr(routes_mod, "cache_set", _mock_cache_set)
    monkeypatch.setattr(routes_mod, "cache_delete", _mock_cache_delete)
    _cache_store.clear()


@pytest.fixture(autouse=True)
def reset_users():
    import app.api.routes as routes_mod

    routes_mod._USERS.clear()
    yield
    routes_mod._USERS.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "project" in data
    assert "version" in data


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_register_and_login():
    # Register a new user
    reg = client.post("/api/v1/auth/register", json={"username": "testuser", "password": "secret123"})
    assert reg.status_code == 201
    assert reg.json()["username"] == "testuser"

    # Login
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"


def test_register_duplicate():
    client.post("/api/v1/auth/register", json={"username": "dupuser", "password": "password1"})
    response = client.post("/api/v1/auth/register", json={"username": "dupuser", "password": "password1"})
    assert response.status_code == 400


def test_login_wrong_password():
    client.post("/api/v1/auth/register", json={"username": "badpass", "password": "correct1"})
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "badpass", "password": "wrongpwd"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Items (protected)
# ---------------------------------------------------------------------------

def _get_token(username: str = "itemsuser", password: str = "itemspass") -> str:
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    return login.json()["access_token"]


def test_list_items_unauthenticated():
    response = client.get("/api/v1/items/")
    assert response.status_code == 401


def test_list_items_authenticated():
    token = _get_token()
    response = client.get("/api/v1/items/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "data" in response.json()


def test_get_item_authenticated():
    token = _get_token(username="getitemuser", password="password1")
    response = client.get("/api/v1/items/my-item", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "my-item"


def test_delete_item_authenticated():
    token = _get_token(username="deluser", password="password1")
    response = client.delete("/api/v1/items/to-delete", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
