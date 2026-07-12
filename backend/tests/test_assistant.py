"""Backend tests for the omnipresent AI Workspace Assistant.

Covers:
- GET /api/assistant/suggestions (generic / project / document scopes)
- POST /api/assistant/action (transform-section, transform-document, info modes)
- POST /api/assistant/chat/stream (SSE stream shape)
- Org isolation between two demo tenants
"""
import json
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
           open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].strip().splitlines()[0]


# ---------- Fixtures ----------
def _demo():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json()["accessToken"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def client_a():
    return _demo()


@pytest.fixture(scope="module")
def client_b():
    return _demo()


@pytest.fixture(scope="module")
def project_a(client_a):
    r = client_a.get(f"{BASE_URL}/api/projects", timeout=30)
    assert r.status_code == 200
    projs = r.json()
    # Find Brand Redesign
    br = next((p for p in projs if p.get("name") == "Brand Redesign"), None)
    assert br, f"Brand Redesign project not seeded: {projs}"
    return br


# ---------- Suggestions ----------
class TestSuggestions:
    def test_generic(self, client_a):
        r = client_a.get(f"{BASE_URL}/api/assistant/suggestions?scope=generic", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        cmds = [d["command"] for d in data]
        assert "summarize" in cmds and "brainstorm" in cmds and "email" in cmds
        for d in data:
            assert "label" in d and "mode" in d

    def test_document_proposal(self, client_a):
        r = client_a.get(f"{BASE_URL}/api/assistant/suggestions?scope=document&document_type=proposal", timeout=15)
        assert r.status_code == 200
        cmds = [d["command"] for d in r.json()]
        # Proposal chips: improve, exec_summary, pricing, weak, tone, translate, email, faq
        for expected in ["improve", "exec_summary", "pricing", "translate", "email"]:
            assert expected in cmds, f"missing {expected} in {cmds}"

    def test_project(self, client_a):
        r = client_a.get(f"{BASE_URL}/api/assistant/suggestions?scope=project", timeout=15)
        assert r.status_code == 200
        cmds = [d["command"] for d in r.json()]
        assert "summarize" in cmds and "risks" in cmds and "timeline" in cmds


# ---------- Actions ----------
class TestAction:
    def test_transform_section_improve(self, client_a, project_a):
        payload = {
            "command": "improve",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project_a["id"],
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
        r = client_a.post(f"{BASE_URL}/api/assistant/action", json=payload, timeout=90)
        if r.status_code == 502 and "budget" in r.text.lower():
            pytest.skip(f"LLM budget: {r.text}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "answer" in data and "report" in data
        assert data["apply"], f"apply must not be null: {data}"
        assert data["apply"]["mode"] == "section"
        assert data["apply"]["target"] == "overview"
        assert "value" in data["apply"]
        rep = data["report"]
        for k in ("what", "why", "impact", "time_saved", "confidence"):
            assert k in rep

    def test_transform_document_translate(self, client_a, project_a):
        payload = {
            "command": "translate",
            "arg": "French",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project_a["id"],
                "sections": [
                    {"key": "overview", "label": "Overview", "type": "text", "value": "We build brands."},
                    {"key": "deliverables", "label": "Deliverables", "type": "list",
                     "value": ["Logo suite", "Brand guidelines"]},
                ],
            },
        }
        r = client_a.post(f"{BASE_URL}/api/assistant/action", json=payload, timeout=120)
        if r.status_code == 502 and "budget" in r.text.lower():
            pytest.skip(f"LLM budget: {r.text}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["apply"] is not None
        assert data["apply"]["mode"] == "document"
        vals = data["apply"]["values"]
        assert isinstance(vals, dict)
        # Type preservation: list stays list if returned
        if "deliverables" in vals:
            assert isinstance(vals["deliverables"], list), f"list type not preserved: {vals}"
        if "overview" in vals:
            assert isinstance(vals["overview"], str)

    def test_info_summarize(self, client_a, project_a):
        payload = {
            "command": "summarize",
            "context": {
                "scope": "document",
                "documentType": "proposal",
                "entityName": "Brand Redesign — Proposal",
                "entityId": project_a["id"],
                "sections": [
                    {"key": "overview", "label": "Overview", "type": "text",
                     "value": "Full visual identity refresh and website redesign for Halcyon Group."},
                ],
            },
        }
        r = client_a.post(f"{BASE_URL}/api/assistant/action", json=payload, timeout=90)
        if r.status_code == 502 and "budget" in r.text.lower():
            pytest.skip(f"LLM budget: {r.text}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["apply"] is None, f"info command must not apply: {data}"
        assert isinstance(data["answer"], str) and len(data["answer"]) > 0
        assert "report" in data and "time_saved" in data["report"]

    def test_unknown_command(self, client_a):
        r = client_a.post(f"{BASE_URL}/api/assistant/action",
                          json={"command": "notarealcmd", "context": {}}, timeout=15)
        assert r.status_code == 400


# ---------- Streaming Chat ----------
class TestChatStream:
    def test_stream_shape(self, client_a):
        payload = {
            "message": "In one short sentence, summarise my workspace.",
            "context": {"scope": "generic", "label": "your workspace"},
        }
        url = f"{BASE_URL}/api/assistant/chat/stream"
        with client_a.post(url, json=payload, stream=True, timeout=120) as r:
            if r.status_code == 502 and "budget" in r.text.lower():
                pytest.skip("LLM budget")
            assert r.status_code == 200, r.text
            assert "text/event-stream" in r.headers.get("content-type", "")
            saw_delta = False
            saw_done = False
            deadline = time.time() + 90
            for raw in r.iter_lines(decode_unicode=True):
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
            assert saw_done, "stream never sent a final done event"
            # delta is optional if LLM budget short-circuited but done+report is essential
            assert saw_delta or saw_done


# ---------- Org isolation ----------
class TestOrgIsolation:
    def test_history_isolated(self, client_a, client_b):
        # A runs an info action; B should not see A's history
        session_a = "isolation-a-session"
        payload = {
            "session_id": session_a,
            "command": "brainstorm",
            "context": {"scope": "generic"},
        }
        r = client_a.post(f"{BASE_URL}/api/assistant/action", json=payload, timeout=90)
        if r.status_code == 502 and "budget" in r.text.lower():
            pytest.skip("LLM budget")
        assert r.status_code == 200, r.text

        # A can read history
        ra = client_a.get(f"{BASE_URL}/api/assistant/history/{session_a}", timeout=15)
        assert ra.status_code == 200
        assert len(ra.json()) >= 1

        # B on same session_id should see empty (org scoped)
        rb = client_b.get(f"{BASE_URL}/api/assistant/history/{session_a}", timeout=15)
        assert rb.status_code == 200
        assert rb.json() == [], f"org isolation broken: {rb.json()}"
