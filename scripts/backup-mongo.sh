#!/usr/bin/env bash
# MongoDB Atlas / self-hosted backup helper (no credentials stored).
# Usage:
#   export MONGO_URL='mongodb+srv://...'
#   export DB_NAME='assistify'
#   ./scripts/backup-mongo.sh /path/to/backups
set -euo pipefail
OUT_DIR="${1:-./backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${OUT_DIR}/${DB_NAME:-assistify}-${STAMP}"
mkdir -p "$DEST"
if [[ -z "${MONGO_URL:-}" ]]; then
  echo "MONGO_URL is required" >&2
  exit 1
fi
echo "Backing up ${DB_NAME:-assistify} → ${DEST}"
mongodump --uri="$MONGO_URL" --db="${DB_NAME:-assistify}" --out="$DEST"
echo "Done. Store ${DEST} securely. Restore with:"
echo "  mongorestore --uri=\"\$MONGO_URL\" --nsInclude=\"${DB_NAME:-assistify}.*\" ${DEST}"
