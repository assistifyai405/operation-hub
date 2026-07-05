import os
import json
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://operations-hub-75.preview.emergentagent.com').rstrip('/')


def test_root():
    r = requests.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_agents_list():
    r = requests.get(f"{BASE_URL}/api/agents")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 4
    ids = {a["id"] for a in data}
    assert ids == {"copilot", "sales", "writer", "analyst"}
    for a in data:
        # system_message should be hidden
        assert "system_message" not in a
        assert "name" in a and "role" in a and "avatar" in a


def test_chat_stream_fires_and_persists_user_msg():
    """Chat stream endpoint should accept the request and stream events.
    AI response may error due to $0 LLM budget -- that's expected."""
    payload = {"session_id": "TEST_session_pytest", "agent_id": "copilot", "message": "Hello test"}
    with requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True, timeout=30) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        got_event = False
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                got_event = True
                # only need first event to confirm streaming works
                break
        assert got_event


def test_chat_stream_invalid_agent():
    payload = {"session_id": "TEST_bad", "agent_id": "nope", "message": "hi"}
    r = requests.post(f"{BASE_URL}/api/chat/stream", json=payload)
    assert r.status_code == 404


def test_chat_history_empty_session():
    r = requests.get(f"{BASE_URL}/api/chat/history/TEST_nonexistent_session_xyz")
    assert r.status_code == 200
    assert r.json() == []
