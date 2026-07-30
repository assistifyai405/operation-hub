"""Storage provider layer.

STORAGE_PROVIDER=local     → filesystem under UPLOAD_DIR (default for development)
STORAGE_PROVIDER=emergent  → Emergent object storage (optional; needs EMERGENT_LLM_KEY)

Public API (unchanged for callers):
  init_storage(), put_object(path, data, content_type), get_object(path),
  guess_content_type, category_for, human_size, APP_NAME
"""
from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "assistify-os"
_storage_key = None

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif",
    "webp": "image/webp", "svg": "image/svg+xml", "pdf": "application/pdf",
    "json": "application/json", "csv": "text/csv", "txt": "text/plain",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "zip": "application/zip",
}


class StorageError(RuntimeError):
    pass


def _provider() -> str:
    try:
        from config import get_settings
        return get_settings().storage_provider
    except Exception:
        return (os.environ.get("STORAGE_PROVIDER") or "local").lower()


def _upload_dir() -> Path:
    try:
        from config import get_settings
        raw = get_settings().upload_dir
    except Exception:
        raw = os.environ.get("UPLOAD_DIR") or os.path.join(os.path.dirname(__file__), "uploads")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_local_path(storage_path: str) -> Path:
    """Resolve storage_path under UPLOAD_DIR; reject path traversal and absolute escapes."""
    if not storage_path or not isinstance(storage_path, str):
        raise StorageError("Invalid storage path")
    # Normalize separators and strip leading slashes / drive tricks
    cleaned = storage_path.replace("\\", "/").lstrip("/")
    if ".." in cleaned.split("/"):
        raise StorageError("Path traversal denied")
    root = _upload_dir()
    full = (root / cleaned).resolve()
    try:
        full.relative_to(root)
    except ValueError as e:
        raise StorageError("Path escapes upload directory") from e
    return full


# ---------------- Emergent backend ----------------
def _init_emergent():
    global _storage_key
    if _storage_key:
        return _storage_key
    key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not key:
        try:
            from config import get_settings
            key = (get_settings().emergent_llm_key or "").strip()
        except Exception:
            pass
    if not key:
        raise StorageError(
            "STORAGE_PROVIDER=emergent requires EMERGENT_LLM_KEY. "
            "Set EMERGENT_LLM_KEY or use STORAGE_PROVIDER=local."
        )
    import requests
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _reset_key():
    global _storage_key
    _storage_key = None


def _put_emergent(path: str, data: bytes, content_type: str) -> dict:
    import requests
    for attempt in range(3):
        key = _init_emergent()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
        if resp.status_code == 403:
            _reset_key()
            continue
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def _get_emergent(path: str) -> Tuple[bytes, str]:
    import requests
    for attempt in range(3):
        key = _init_emergent()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
        if resp.status_code == 403:
            _reset_key()
            continue
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    resp.raise_for_status()


# ---------------- Local filesystem backend ----------------
def _put_local(path: str, data: bytes, content_type: str) -> dict:
    full = _safe_local_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    # Persist a tiny sidecar for content-type (optional; get falls back to guess)
    meta = full.with_suffix(full.suffix + ".meta")
    try:
        meta.write_text(content_type or "application/octet-stream", encoding="utf-8")
    except Exception:
        pass
    # Return path relative to upload root (same string callers stored)
    return {"path": path.replace("\\", "/").lstrip("/"), "size": len(data)}


def _get_local(path: str) -> Tuple[bytes, str]:
    full = _safe_local_path(path)
    if not full.is_file():
        raise StorageError("File not found")
    content = full.read_bytes()
    ctype = "application/octet-stream"
    meta = full.with_suffix(full.suffix + ".meta")
    if meta.is_file():
        try:
            ctype = meta.read_text(encoding="utf-8").strip() or ctype
        except Exception:
            ctype = guess_content_type(full.name)
    else:
        ctype = guess_content_type(full.name)
    return content, ctype


# ---------------- Public facade ----------------
def init_storage():
    """Initialize the active storage provider (no-op for local)."""
    provider = _provider()
    if provider == "local":
        root = _upload_dir()
        logger.info("Local storage ready at %s", root)
        return str(root)
    if provider == "emergent":
        return _init_emergent()
    raise StorageError(f"Unknown STORAGE_PROVIDER: {provider}")


def put_object(path: str, data: bytes, content_type: str) -> dict:
    provider = _provider()
    if provider == "local":
        return _put_local(path, data, content_type)
    if provider == "emergent":
        return _put_emergent(path, data, content_type)
    raise StorageError(f"Unknown STORAGE_PROVIDER: {provider}")


def get_object(path: str):
    provider = _provider()
    if provider == "local":
        return _get_local(path)
    if provider == "emergent":
        return _get_emergent(path)
    raise StorageError(f"Unknown STORAGE_PROVIDER: {provider}")


def guess_content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, "application/octet-stream")


def category_for(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "svg"):
        return "Image"
    if ext == "pdf":
        return "PDF"
    if ext in ("doc", "docx", "txt"):
        return "Doc"
    if ext in ("xls", "xlsx", "csv"):
        return "Sheet"
    if ext in ("zip",):
        return "Archive"
    return "Other"


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
