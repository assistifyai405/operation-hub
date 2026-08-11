"""Sprint 29 locale preference and AI language behavior tests."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from locale_util import (  # noqa: E402
    language_instruction_for_user,
    normalize_locale,
    with_language_instruction,
)


@pytest.fixture
def client(api_client):
    client, _ = api_client
    return client


@pytest.fixture
def auth(client):
    return register_user(
        client,
        company=f"LocaleOrg-{uuid.uuid4().hex[:6]}",
        first="Locale",
        last="Tester",
    )


def test_profile_rejects_unsupported_language(client, auth):
    response = client.patch(
        "/api/auth/profile",
        headers=auth["headers"],
        json={"language": "de"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "language must be 'nl' or 'en'"
    me = client.get("/api/auth/me", headers=auth["headers"])
    assert me.status_code == 200
    assert me.json()["language"] == "en"


@pytest.mark.parametrize("language", ["nl", "en"])
def test_profile_accepts_and_persists_supported_language(client, auth, language):
    response = client.patch(
        "/api/auth/profile",
        headers=auth["headers"],
        json={"language": language},
    )

    assert response.status_code == 200, response.text
    assert response.json()["language"] == language

    me = client.get("/api/auth/me", headers=auth["headers"])
    assert me.status_code == 200
    assert me.json()["language"] == language


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("nl", "Preferred response language: Dutch (Nederlands)."),
        ("en", "Preferred response language: English."),
    ],
)
def test_ai_language_instruction_uses_user_preference(language, expected):
    instruction = language_instruction_for_user({"language": language})
    prompt = with_language_instruction("You are Assistify Copilot.", {"language": language})

    assert expected in instruction
    assert prompt.startswith("You are Assistify Copilot.\n\n")
    assert expected in prompt


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("nl-NL", "nl"),
        ("en-US", "en"),
        ("de-DE", "en"),
    ],
)
def test_normalize_locale(raw, expected):
    assert normalize_locale(raw) == expected
