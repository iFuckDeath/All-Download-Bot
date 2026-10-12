# Deployment runbook

## Supabase
Create a project and use its PostgreSQL connection URL with SSL enabled. Use a database password stored in a password manager. The bot connects directly to PostgreSQL; no Supabase service-role key is required.

## Render
1. Push this folder to a private Git repository.
2. Create a Docker Background Worker from the repo.
3. Choose the desired Scale plan and set `BOT_TOKEN`, `ADMIN_IDS`, and `DATABASE_URL` as secrets.
4. Start command: `python -m app.main`.
5. Run exactly one active long-polling worker per Telegram bot token.

## Independent backups
1. Create a private S3-compatible bucket under credentials independent of Render.
2. Set `BACKUP_S3_ENDPOINT_URL` (if required), `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`, `BACKUP_S3_REGION`, and `BACKUP_PREFIX`.
3. Schedule `bash scripts/backup.sh` every 15 minutes in a separate Cron Job or independent scheduler with PostgreSQL client tools and Python dependencies.
4. Configure object lifecycle retention (e.g. 30 daily recovery points) and backup-failure alerts.
5. Test restores monthly in a separate database. Never restore over production during a test.

## Restore
Download and decompress a backup, then restore into a separate PostgreSQL database:
```bash
gunzip -c supabase-YYYYMMDDTHHMMSSZ.dump.gz > restore.dump
pg_restore --no-owner --no-privileges --clean --if-exists --dbname="$TEST_DATABASE_URL" restore.dump
```

## Monthly Render account change
Deploy the same commit to the new account with the same external Supabase and backup bucket. Stop the old polling worker before starting the new one; two long-polling workers with one token conflict. Test `/ping`, `/stats`, `/health`, a permitted URL, and the latest backup. Keep the old service stopped for rollback until verified.

A 15-minute export is near-real-time, not true real-time replication; for near-zero data loss, use an appropriate PITR/continuous-replication service and test failover.
