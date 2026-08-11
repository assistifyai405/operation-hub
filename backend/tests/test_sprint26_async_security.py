"""Sprint 26 — async workers, heartbeats, org scoping, OpenAI config safety."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

import pytest
from conftest import auth_json, ensure_test_settings

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()
    try:
        from redis_client import get_redis
        r = get_redis()
        if r:
            for k in list(r.scan_iter("assistify:rl:*")):
                r.delete(k)
    except Exception:
        pass


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register(client, company="S26 Co"):
    _clear_rl()
    email = f"s26_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "S26",
            "lastName": "User",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    return email, data, {"Authorization": f"Bearer {data['accessToken']}"}


def test_public_config_has_no_openai_key(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    text = r.text.lower()
    assert "sk-" not in text
    assert "openai_api_key" not in text


def test_no_sk_test_in_runtime_compose():
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text()
    assert "sk-test-not-used" not in compose
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY" in compose
    assert 'WORKER_ENABLED: "true"' in compose
    assert 'SCHEDULER_ENABLED: "true"' in compose
    assert 'REQUIRE_REDIS: "true"' in compose


def test_job_enqueue_process_idempotency_and_failure(api_client, monkeypatch):
    """Redis-backed job E2E using real Redis when available."""
    client, _ = api_client
    ensure_test_settings()
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL") or "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("REQUIRE_REDIS", "false")
    from config import reset_settings_for_tests, load_settings
    reset_settings_for_tests()
    load_settings(strict=True)

    from redis_client import ping_redis, get_redis
    import redis_client as rc
    rc._client = None
    rc._available = None
    rp = ping_redis()
    if not rp.get("ok"):
        pytest.skip("Redis not available for job E2E")

    import jobs.handlers  # noqa: F401
    from jobs import enqueue, process_one_from_queue, QUEUE_KEY, FAILED_KEY, run_job
    from jobs.heartbeats import beat, read_status, clear
    from distributed_locks import distributed_lock

    async def _run():
        r = get_redis(force=True)
        while r.llen(QUEUE_KEY):
            raw = r.rpop(QUEUE_KEY)
            if not raw:
                break

        key = f"s26-noop:{uuid.uuid4().hex}"
        doc1 = await enqueue("test_noop", organization_id="org_test", payload={"echo": "hi"}, idempotency_key=key)
        doc2 = await enqueue("test_noop", organization_id="org_test", payload={"echo": "hi"}, idempotency_key=key)
        assert doc1["id"] == doc2["id"]

        processed = None
        for _ in range(20):
            processed = await process_one_from_queue()
            if processed and processed.get("id") == doc1["id"]:
                break
            await asyncio.sleep(0.05)
        assert processed is not None
        assert processed.get("status") == "succeeded"
        assert (processed.get("result") or {}).get("echo") == "hi"

        fail = await enqueue("test_fail", organization_id="org_test", payload={}, max_attempts=2)
        await run_job(fail["id"])
        out2 = await run_job(fail["id"])
        final = out2 if out2.get("status") == "failed" else await run_job(fail["id"])
        assert final.get("status") == "failed"
        assert r.llen(FAILED_KEY) >= 1 or final.get("status") == "failed"

        clear("worker")
        clear("scheduler")
        assert beat("worker")
        assert beat("scheduler")
        assert read_status("worker")["status"] == "running"
        assert read_status("scheduler")["status"] == "running"

        async with distributed_lock("s26:test", ttl_seconds=5, prefix="sched"):
            held = True
        assert held

    try:
        client.portal.call(_run)
    finally:
        ensure_test_settings()
        rc._client = None
        rc._available = None


def test_ready_reports_heartbeat_honesty(client, monkeypatch):
    ensure_test_settings()
    from redis_client import ping_redis
    import redis_client as rc
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL") or "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("REQUIRE_REDIS", "true")
    from config import reset_settings_for_tests, load_settings
    reset_settings_for_tests()
    load_settings(strict=True)
    rc._client = None
    rc._available = None
    if not ping_redis().get("ok"):
        ensure_test_settings()
        pytest.skip("Redis required for heartbeat ready test")

    from jobs.heartbeats import clear, beat
    try:
        clear("worker")
        clear("scheduler")

        # Without heartbeats + require redis → degraded
        r = client.get("/api/health/ready")
        assert r.status_code == 503
        body = r.json()
        jobs = body["checks"]["jobs"]
        assert jobs["workerEnabled"] is True
        assert jobs["schedulerEnabled"] is True
        assert jobs["syncMode"] is False
        assert jobs["worker"]["status"] in ("unavailable", "stale")
        assert "worker" in body["failedChecks"] or "scheduler" in body["failedChecks"]

        beat("worker")
        beat("scheduler")
        r2 = client.get("/api/health/ready")
        assert r2.status_code == 200, r2.text
        jobs2 = r2.json()["checks"]["jobs"]
        assert jobs2["worker"]["status"] == "running"
        assert jobs2["scheduler"]["status"] == "running"
        assert jobs2["syncMode"] is False
    finally:
        clear("worker")
        clear("scheduler")
        ensure_test_settings()
        rc._client = None
        rc._available = None


def test_artifact_and_context_isolation(client):
    _, a, hA = _register(client, company="IsoA")
    _, b, hB = _register(client, company="IsoB")

    cr = client.post("/api/clients", headers=hA, json={"name": "SecretA", "contact": "A", "email": "a@iso.test"})
    assert cr.status_code == 200
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=hA, json={"name": "SecretProjA", "client_id": cid, "status": "Active"})
    assert pr.status_code == 200
    pid = pr.json()["id"]

    # Save a proposal for A
    save = client.post(
        f"/api/projects/{pid}/proposal",
        headers=hA,
        json={"title": "Secret Proposal", "status": "Draft", "content": {"summary": "CONFIDENTIAL_A"}},
    )
    assert save.status_code == 200, save.text

    # B cannot GET proposal / plans / activities / generate
    assert client.get(f"/api/projects/{pid}/proposal", headers=hB).status_code in (403, 404)
    assert client.get(f"/api/projects/{pid}/plans", headers=hB).status_code in (403, 404)
    assert client.get(f"/api/activities?project_id={pid}", headers=hB).status_code in (403, 404)
    assert client.post(f"/api/projects/{pid}/proposal/generate", headers=hB).status_code in (403, 404)

    # B cannot plant task/doc onto A's project
    assert client.post(
        "/api/tasks",
        headers=hB,
        json={"title": "Plant", "project_id": pid, "priority": "High", "done": False},
    ).status_code in (403, 404)
    assert client.post(
        "/api/documents",
        headers=hB,
        json={"name": "Plant Doc", "type": "Doc", "project_id": pid, "size": "1"},
    ).status_code in (403, 404)

    # A still sees own proposal
    got = client.get(f"/api/projects/{pid}/proposal", headers=hA)
    assert got.status_code == 200
    assert "CONFIDENTIAL_A" in got.text


def test_ai_context_builder_org_scoped(api_client):
    """build_project_context must not mix foreign org tasks/docs/activities."""
    client, _ = api_client
    ensure_test_settings()
    from core import db, now_iso
    from server import build_project_context

    async def _run():
        org_a = f"orga_{uuid.uuid4().hex[:8]}"
        org_b = f"orgb_{uuid.uuid4().hex[:8]}"
        pid = f"proj_{uuid.uuid4().hex[:8]}"
        await db.projects.insert_one({
            "id": pid, "organizationId": org_a, "name": "Ctx Proj", "status": "Active",
            "client_name": None, "progress": 0, "due": None, "members": 1,
            "description": "", "notes": "", "created_at": now_iso(),
        })
        await db.tasks.insert_one({
            "id": f"t_{uuid.uuid4().hex[:8]}", "organizationId": org_a, "project_id": pid,
            "title": "OWN_TASK_MARKER", "priority": "High", "done": False, "created_at": now_iso(),
        })
        await db.tasks.insert_one({
            "id": f"t_{uuid.uuid4().hex[:8]}", "organizationId": org_b, "project_id": pid,
            "title": "FOREIGN_TASK_MARKER", "priority": "High", "done": False, "created_at": now_iso(),
        })
        try:
            project = await db.projects.find_one({"id": pid, "organizationId": org_a}, {"_id": 0})
            ctx = await build_project_context(project)
            assert "OWN_TASK_MARKER" in ctx
            assert "FOREIGN_TASK_MARKER" not in ctx
        finally:
            await db.projects.delete_many({"id": pid})
            await db.tasks.delete_many({"project_id": pid})

    client.portal.call(_run)


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AI_TESTS", "").lower() not in {"1", "true", "yes", "on"},
    reason="Set RUN_LIVE_AI_TESTS=true with OPENAI_API_KEY to run live AI smoke",
)
def test_live_ai_smoke_optional():
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key or key.startswith("sk-test"):
        pytest.skip("OPENAI_API_KEY not configured for live smoke")
    ensure_test_settings()
    from ai_service import AIService, public_ai_error

    async def _call():
        svc = AIService(api_key=key, provider="openai", model=os.environ.get("AI_MODEL") or "gpt-4o-mini")
        text = await svc.complete("Reply with exactly: pong", "ping")
        return text

    text = asyncio.run(_call())
    assert text
    assert "sk-" not in text.lower()
    # Sanitizer still safe
    assert "sk-live" not in public_ai_error(Exception("Incorrect API key provided: sk-live-xxx")).lower()
