"""
Shared pytest fixtures.

A single session-scoped TestClient avoids Motor/asyncio event-loop conflicts
when multiple HTTP test modules would otherwise each create their own client.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from starlette.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "backend" / ".env", override=False)

_TEST_ENV = {
    "ENVIRONMENT": "development",
    "MONGO_URL": "mongodb://127.0.0.1:27017",
    "DB_NAME": "assistify_test",
    "JWT_SECRET": "unit-test-secret-key-with-32plus-chars!!",
    "AI_PROVIDER": "openai",
    "OPENAI_API_KEY": "sk-test-key",
    "STORAGE_PROVIDER": "local",
    "UPLOAD_DIR": "/tmp/assistify-test-uploads",
    "FRONTEND_URL": "http://localhost:3000",
    "CORS_ORIGINS": "http://localhost:3000",
    "ENABLE_DEMO_SEED": "false",
    "INVITATION_EXPIRY_DAYS": "7",
}

for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)


def ensure_test_settings():
    """Restore process-wide settings after unit tests that clear the cache."""
    from config import load_settings, reset_settings_for_tests

    for k, v in _TEST_ENV.items():
        os.environ[k] = v
    reset_settings_for_tests()
    return load_settings(strict=True)


@pytest.fixture(scope="session")
def api_client():
    # Settings must be loaded before importing server (CORS reads them at import).
    ensure_test_settings()
    upload_dir = os.environ["UPLOAD_DIR"]
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    from server import app
    import dependencies as deps

    with TestClient(app) as client:
        yield client, upload_dir
    deps._rl_store.clear()
