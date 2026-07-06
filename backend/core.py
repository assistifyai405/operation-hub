import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from ai_service import AIService

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
ai_service = AIService(api_key=EMERGENT_LLM_KEY)


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
