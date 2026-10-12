#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${DATABASE_URL:?DATABASE_URL required}"
: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET required}"
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 2; }
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
pg_dump --format=custom --no-owner --no-privileges --file="$WORK/db.dump" "$DATABASE_URL"
gzip -c "$WORK/db.dump" > "$WORK/db.dump.gz"
python scripts/backup_upload.py "$WORK/db.dump.gz" "supabase-${STAMP}.dump.gz"
echo "Backup uploaded: supabase-${STAMP}.dump.gz"
