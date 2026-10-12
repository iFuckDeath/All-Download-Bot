# Feature status

## In this starter
- Clean Telegram UI, colored inline buttons and Unicode emoji fallback
- `/start`, `/help`, `/platforms`, `/about`, `/ping`, `/stats`, `/cancel`, `/report`
- Admin `/admin`, `/health`, `/users`, `/ban`, `/unban`
- yt-dlp metadata and format selection; video/audio download and Telegram delivery
- Supabase PostgreSQL persistence for users, jobs, reports, donation records and audit logs
- URL scheme, DNS and public-IP validation; per-user and global concurrency limits
- Job timeout, conservative 49 MiB cap, temporary-file cleanup
- Independent compressed PostgreSQL backup to S3-compatible storage

## Before public launch
- Playlist batch processing and archive splitting
- Telegram Stars invoices and successful-payment validation
- Admin broadcast preview/confirm and resumable delivery
- Durable queue and job recovery after process restart
- Channel invitation sent-once timestamp
- Robust egress-level SSRF protections for redirects, DNS rebinding and extractor network requests
- Backup schedule monitoring/alerts, retention lifecycle and restore tests
- Load tests, metrics, privacy/retention policy and graceful shutdown
- Optional custom emoji IDs, only if eligible

Do not advertise unfinished features as live. Keep the bot private during initial testing.
