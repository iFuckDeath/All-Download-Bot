# Telegram Media Bot

Telegram-only media downloader starter using Python 3.12, aiogram 3, yt-dlp, Supabase PostgreSQL and Render Background Worker.

## Safe-use boundaries
Downloads are for media the user is authorized to access and save. No DRM, paywall, login, age-verification or other access-control bypass. Adult-site URLs are supported only when lawful and accessible without bypassing restrictions. Platform support changes; not every URL is guaranteed to work. No website frontend or website fallback is included.

## Local setup
1. Create a bot with Telegram's BotFather.
2. Create a Supabase PostgreSQL project.
3. Copy `.env.example` to `.env` and set secrets.
4. Install Python 3.12 and FFmpeg, then run:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m app.main
   ```
5. Set `ADMIN_IDS` to your numeric Telegram ID. Never commit `.env`.

## Render
Deploy as a Docker Background Worker. Start command: `python -m app.main`. Run exactly one active long-polling worker for each bot token. Render files are ephemeral, so only use them for temporary media.

## Backups
Use a private S3-compatible bucket under credentials independent of Render (and ideally independent of Supabase). Schedule `bash scripts/backup.sh` every 15 minutes using a separate Cron Job or independent scheduler. It requires `pg_dump`, Python, and the packages in `requirements.txt`. Configure object lifecycle retention and failure alerts. Test restores monthly. A 15-minute dump is near-real-time, not zero-RPO replication; use PITR/continuous replication for lower data loss.

## Starter limitations
This is a clean foundation, not yet a full public-launch release. Playlist batches, Stars payments, resumable broadcasts, durable job recovery, robust network-level SSRF protection, alerting, and full custom-emoji configuration remain hardening tasks. Keep it private while testing.
