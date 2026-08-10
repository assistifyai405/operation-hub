"""AI Agents list endpoint — auth required, static personas, no secrets."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register(client):
    _clear_rl()
    email = f"agents_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Agent",
            "lastName": "Tester",
            "email": email,
            "password": "Password123!",
            "company": "Agents Co",
        },
    )
    assert r.status_code == 200, r.text
    return auth_json(client, r)


def test_agents_requires_auth(client):
    client.cookies.clear()
    r = client.get("/api/agents")
    # Unauthenticated requests must not return the agents array
    assert r.status_code in (401, 403)
    body = r.json()
    assert not isinstance(body, list)
    assert "detail" in body or "error" in body


def test_agents_list_authenticated(client):
    data = _register(client)
    token = data["accessToken"]
    r = client.get("/api/agents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    agents = r.json()
    assert isinstance(agents, list)
    assert len(agents) == 4
    ids = {a["id"] for a in agents}
    assert ids == {"copilot", "sales", "writer", "analyst"}
    for a in agents:
        assert "system_message" not in a
        assert a.get("name")
        assert a.get("role")
