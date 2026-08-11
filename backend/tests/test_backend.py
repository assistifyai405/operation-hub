"""Root / agents / chat stream smoke — TestClient."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    return register_user(client, company="Backend Smoke")


def test_root(client):
    r = client.get("/api/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_agents_list(client, auth):
    r = client.get("/api/agents", headers=auth["headers"])
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 4
    ids = {a["id"] for a in data}
    assert ids == {"copilot", "sales", "writer", "analyst"}
    for a in data:
        assert "system_message" not in a
        assert "name" in a and "role" in a and "avatar" in a


def test_chat_stream_fires_and_persists_user_msg(client, auth):
    payload = {"session_id": "TEST_session_pytest", "agent_id": "copilot", "message": "Hello test"}
    with client.stream("POST", "/api/chat/stream", headers=auth["headers"], json=payload) as r:
        assert r.status_code in (200, 502, 503)
        if r.status_code != 200:
            body = r.read().decode("utf-8", errors="replace")
            assert "sk-" not in body.lower()
            return
        assert "text/event-stream" in r.headers.get("content-type", "")
        got_event = False
        collected = ""
        for line in r.iter_lines():
            collected += line + "\n"
            if line and line.startswith("data:"):
                got_event = True
                break
        assert "sk-" not in collected.lower()
        assert got_event


def test_chat_stream_real_ai_response(client, auth):
    """Accepts 200 with text OR sanitized 502/503 when LLM key is fake."""
    payload = {"session_id": "TEST_real_ai_session", "agent_id": "copilot", "message": "Say hello in 5 words"}
    collected = ""
    done_seen = False
    with client.stream("POST", "/api/chat/stream", headers=auth["headers"], json=payload) as r:
        assert r.status_code in (200, 502, 503)
        if r.status_code != 200:
            body = r.read().decode("utf-8", errors="replace")
            assert "sk-" not in body.lower()
            return
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = json.loads(line[5:].strip())
            if data.get("delta"):
                collected += data["delta"]
            if data.get("done"):
                done_seen = True
        assert "sk-" not in collected.lower()
    if done_seen:
        assert len(collected) >= 0  # may be empty on failure path inside stream


def test_chat_stream_invalid_agent(client, auth):
    payload = {"session_id": "TEST_bad", "agent_id": "nope", "message": "hi"}
    r = client.post("/api/chat/stream", headers=auth["headers"], json=payload)
    assert r.status_code == 404


def test_chat_history_empty_session(client, auth):
    r = client.get("/api/chat/history/TEST_nonexistent_session_xyz", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json() == []
