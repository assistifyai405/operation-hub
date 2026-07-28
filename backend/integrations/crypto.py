"""Fernet encryption for integration credentials (refresh tokens, webhook secrets).

Never log or return decrypted credentials to the frontend.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    from config import get_settings

    s = get_settings()
    raw = (s.integration_encryption_key or "").strip()
    if raw:
        # Accept url-safe base64 Fernet key, or derive from arbitrary secret
        try:
            return Fernet(raw.encode() if isinstance(raw, str) else raw)
        except Exception:
            digest = hashlib.sha256(raw.encode("utf-8")).digest()
            return Fernet(base64.urlsafe_b64encode(digest))
    # Fallback: derive from JWT_SECRET (still never expose plaintext)
    digest = hashlib.sha256(("integrations:" + s.jwt_secret).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(payload: dict) -> str:
    token = _fernet().encrypt(json.dumps(payload).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_credentials(blob: str) -> dict:
    if not blob:
        return {}
    try:
        raw = _fernet().decrypt(blob.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (InvalidToken, json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to decrypt integration credentials: %s", type(e).__name__)
        raise ValueError("Invalid or corrupted integration credentials") from e


def public_safe(doc: dict) -> dict:
    """Strip secrets from an integration document for API responses."""
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k not in {"_id", "encryptedCredentials", "credentials"}}
    # Never leak raw webhook URLs fully — show host only if present in config
    cfg = dict(out.get("config") or {})
    if "webhookUrl" in cfg:
        cfg["webhookUrlConfigured"] = bool(cfg.pop("webhookUrl", None) or True)
        # Prefer not keeping URL in config at all (stored encrypted); remove if leaked
        cfg.pop("webhookUrl", None)
    if "botToken" in cfg:
        cfg.pop("botToken", None)
        cfg["botTokenConfigured"] = True
    out["config"] = cfg
    return out
