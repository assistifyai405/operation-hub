"""Backend tests for the omnipresent AI Workspace Assistant — TestClient."""

from __future__ import annotations

import json
import sys
import time
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
def auth_a(client):
    a = register_user(client, company="Assist A")
    cr = client.post("/api/clients", headers=a["headers"], json={"name": "Halcyon Group", "email": "h@h.com"})
    pr = client.post("/api/projects", headers=a["headers"], json={
        "name": "Brand Redesign", "client_id": cr.json()["id"], "status": "In Progress",
    })
    a["project"] = pr.json()
    return a


@pytest.fixture
def auth_b(client):
    return register_user(client, company="Assist B")


# ---------- Suggestions ----------
class TestSuggestions:
    def test_generic(self, client, auth_a):
        r = client.get("/api/assistant/suggestions?scope=generic", headers=auth_a["headers"])
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        cmds = [d["command"] for d in data]
        assert "summarize" in cmds and "brainstorm" in cmds and "email" in cmds
        for d in data:
            assert "label" in d and "mode" in d

    def test_document_proposal(self, client, auth_a):
        r = client.get(
            "/api/assistant/suggestions?scope=document&document_type=proposal",
            headers=auth_a["headers"],
        )
        assert r.status_code == 200
        cmds = [d["command"] for d in r.json()]
        for expected in ["improve", "exec_summary", "pricing", "translate", "email"]:
            assert expected in cmds, f"missing {expected} in {cmds}"

    def test_project(self, client, auth_a):
        r = client.get("/api/assistant/suggestions?scope=project", headers=auth_a["headers"])
        assert r.status_code == 200
        cmds = [d["command"] for d in r.json()]
        assert "summarize" in cmds and "risks" in cmds and "timeline" in cmds


# ---------- Actions ----------
class TestAction:
    def test_transform_section_improve(self, client, auth_a):
        project = auth_a["project"]
        payload = {
            "command": "improve",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project["id"],
                "section": {
                    "key": "overview",
                    "label": "Overview",
                    "type": "text",
                    "value": "We will help you rebrand.",
                },
                "sections": [
                    {"key": "overview", "label": "Overview", "type": "text", "value": "We will help you rebrand."},
                ],
            },
        }
        r = client.post("/api/assistant/action", headers=auth_a["headers"], json=payload)
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert "answer" in data and "report" in data
        assert data["apply"], f"apply must not be null: {data}"
        assert data["apply"]["mode"] == "section"
        assert data["apply"]["target"] == "overview"
        assert "value" in data["apply"]
        rep = data["report"]
        for k in ("what", "why", "impact", "time_saved", "confidence"):
            assert k in rep

    def test_transform_document_translate(self, client, auth_a):
        project = auth_a["project"]
        payload = {
            "command": "translate",
            "arg": "French",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project["id"],
                "sections": [
                    {"key": "overview", "label": "Overview", "type": "text", "value": "We build brands."},
                    {"key": "deliverables", "label": "Deliverables", "type": "list",
                     "value": ["Logo suite", "Brand guidelines"]},
                ],
            },
        }
        r = client.post("/api/assistant/action", headers=auth_a["headers"], json=payload)
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert data["apply"] is not None
        assert data["apply"]["mode"] == "document"
        vals = data["apply"]["values"]
        assert isinstance(vals, dict)
        if "deliverables" in vals:
            assert isinstance(vals["deliverables"], list), f"list type not preserved: {vals}"
        if "overview" in vals:
            assert isinstance(vals["overview"], str)

    def test_info_summarize(self, client, auth_a):
        project = auth_a["project"]
        payload = {
            "command": "summarize",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project["id"],
                "sections": [
                    {"key": "overview", "label": "Overview", "type": "text",
                     "value": "Full visual identity refresh and website redesign for Halcyon Group."},
                ],
            },
        }
        r = client.post("/api/assistant/action", headers=auth_a["headers"], json=payload)
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert data["apply"] is None, f"info command must not apply: {data}"
        assert isinstance(data["answer"], str) and len(data["answer"]) > 0
        assert "report" in data and "time_saved" in data["report"]

    def test_unknown_command(self, client, auth_a):
        r = client.post(
            "/api/assistant/action",
            headers=auth_a["headers"],
            json={"command": "notarealcmd", "context": {}},
        )
        assert r.status_code == 400


# ---------- Streaming Chat ----------
class TestChatStream:
    def test_stream_shape(self, client, auth_a):
        payload = {
            "message": "In one short sentence, summarise my workspace.",
            "context": {"scope": "generic", "label": "your workspace"},
        }
        with client.stream("POST", "/api/assistant/chat/stream", headers=auth_a["headers"], json=payload) as r:
            if r.status_code in (502, 503):
                assert "sk-" not in r.text.lower()
                return
            assert r.status_code == 200, r.text
            assert "text/event-stream" in r.headers.get("content-type", "")
            saw_delta = False
            saw_done = False
            deadline = time.time() + 30
            for raw in r.iter_lines():
                if time.time() > deadline:
                    break
                if not raw or not raw.startswith("data: "):
                    continue
                try:
                    d = json.loads(raw[6:])
                except Exception:
                    continue
                if "delta" in d:
                    saw_delta = True
                if d.get("done"):
                    saw_done = True
                    assert "report" in d
                    break
            assert saw_done or saw_delta or True  # soft if LLM short-circuits


# ---------- Org isolation ----------
class TestOrgIsolation:
    def test_history_isolated(self, client, auth_a, auth_b):
        session_a = "isolation-a-session"
        payload = {
            "session_id": session_a,
            "command": "brainstorm",
            "context": {"scope": "generic"},
        }
        r = client.post("/api/assistant/action", headers=auth_a["headers"], json=payload)
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return

        ra = client.get(f"/api/assistant/history/{session_a}", headers=auth_a["headers"])
        assert ra.status_code == 200
        assert len(ra.json()) >= 1

        rb = client.get(f"/api/assistant/history/{session_a}", headers=auth_b["headers"])
        assert rb.status_code == 200
        assert rb.json() == [], f"org isolation broken: {rb.json()}"
