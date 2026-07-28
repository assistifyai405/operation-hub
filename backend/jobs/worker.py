#!/usr/bin/env python3
"""Background worker — poll Redis queue and run jobs.

  cd backend && python -m jobs.worker
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("jobs.worker")


async def main():
    # Load env / settings
    from pathlib import Path
    from dotenv import load_dotenv
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    from config import load_settings
    load_settings()
    import jobs.handlers  # noqa: F401 — register
    from jobs import process_one_from_queue

    logger.info("Worker started")
    idle = 0
    while True:
        try:
            result = await process_one_from_queue()
            if result:
                idle = 0
                logger.info("Processed job id=%s status=%s", result.get("id"), result.get("status"))
            else:
                idle += 1
                await asyncio.sleep(0.5 if idle < 10 else 2)
        except KeyboardInterrupt:
            break
        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(2)
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
