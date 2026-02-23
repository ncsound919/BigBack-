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


class _MockDBSession:
    """Minimal async SQLAlchemy session mock – no real DB required."""

    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass


async def _override_get_db():
    yield _MockDBSession()


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    import app.api.routes as routes_mod

    monkeypatch.setattr(routes_mod, "cache_get", _mock_cache_get)
    monkeypatch.setattr(routes_mod, "cache_set", _mock_cache_set)
    monkeypatch.setattr(routes_mod, "cache_delete", _mock_cache_delete)
    _cache_store.clear()


@pytest.fixture(autouse=True)
def override_db_dependency():
    from app.db.database import get_db

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


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


# ---------------------------------------------------------------------------
# Items – create (POST)
# ---------------------------------------------------------------------------

def test_create_item_authenticated():
    token = _get_token(username="createuser", password="password1")
    response = client.post(
        "/api/v1/items/",
        json={"name": "new-item", "description": "A test item"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new-item"
    assert data["description"] == "A test item"
    assert data["owner"] == "createuser"
    assert "id" in data


def test_create_item_unauthenticated():
    response = client.post("/api/v1/items/", json={"name": "x"})
    assert response.status_code == 401


def test_create_item_missing_name():
    token = _get_token(username="noname", password="password1")
    response = client.post(
        "/api/v1/items/",
        json={"description": "no name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def test_list_templates():
    response = client.get("/api/v1/templates/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 8
    ids = [t["id"] for t in data]
    assert "fastapi-crud" in ids
    assert "redis-cache" in ids


def test_list_templates_filter_by_framework():
    response = client.get("/api/v1/templates/?framework=fastapi")
    assert response.status_code == 200
    data = response.json()
    assert all(t["framework"] == "fastapi" for t in data)
    assert len(data) >= 3


def test_get_template_detail():
    response = client.get("/api/v1/templates/fastapi-crud")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "fastapi-crud"
    assert "code" in data
    assert len(data["code"]) > 50


def test_get_template_not_found():
    response = client.get("/api/v1/templates/nonexistent-template")
    assert response.status_code == 404
