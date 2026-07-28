"""Core database + shared services.

Loads dotenv, validates environment via config.load_settings(), then opens Mongo.
AI and storage providers are selected by env (see config.py / README).
"""
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from config import load_settings, get_settings, ConfigError  # noqa: E402
from ai_service import build_ai_service_from_settings, AIService  # noqa: E402

# Validate required env before opening DB connections
settings = load_settings(strict=True)

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.db_name]

# Backward-compatible export: may be None when using OpenAI-only setup
EMERGENT_LLM_KEY = settings.emergent_llm_key or ""

ai_service: AIService = build_ai_service_from_settings()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def log_activity(project_id: Optional[str], atype: str, message: str):
    if not project_id:
        return
    proj = await db.projects.find_one({"id": project_id}, {"_id": 0, "organizationId": 1})
    await db.activities.insert_one({
        "id": str(uuid.uuid4()), "project_id": project_id,
        "organizationId": (proj or {}).get("organizationId"),
        "type": atype, "message": message, "created_at": now_iso(),
    })
