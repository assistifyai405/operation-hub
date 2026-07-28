#!/usr/bin/env python3
"""Poll/sync all enabled mailboxes (Sprint 16). Safe for cron.

Usage (from backend/ with venv active):
  python -m inbox.sync_all
  python -m inbox.sync_all --org ORG_ID --mailbox MAILBOX_ID
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("inbox.sync_all")


async def main(org_id: str | None, mailbox_id: str | None, force_full: bool) -> int:
    from core import db
    from inbox.sync_service import sync_mailbox

    query: dict = {"syncEnabled": True}
    if org_id:
        query["organizationId"] = org_id
    if mailbox_id:
        query["id"] = mailbox_id

    mailboxes = await db.mailboxes.find(query, {"_id": 0}).to_list(500)
    if not mailboxes:
        logger.info("No enabled mailboxes matched")
        return 0

    failures = 0
    for mb in mailboxes:
        try:
            result = await sync_mailbox(
                mb["organizationId"], mb["id"], force_full=force_full,
            )
            logger.info(
                "Synced mailbox=%s org=%s created=%s scanned=%s",
                mb["id"], mb["organizationId"], result.get("messagesCreated"), result.get("messagesScanned"),
            )
        except Exception as e:
            failures += 1
            logger.exception("Sync failed mailbox=%s: %s", mb.get("id"), e)
    return 1 if failures else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Sync Assistify shared inbox mailboxes")
    p.add_argument("--org", dest="org_id", default=None)
    p.add_argument("--mailbox", dest="mailbox_id", default=None)
    p.add_argument("--force-full", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.org_id, args.mailbox_id, args.force_full)))
