import asyncpg

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  telegram_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT, language_code TEXT,
  is_banned BOOLEAN NOT NULL DEFAULT FALSE,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(), last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  channel_invite_sent_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY, telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  source_host TEXT NOT NULL, url_hash TEXT NOT NULL, status TEXT NOT NULL,
  title TEXT, selected_format TEXT, bytes_delivered BIGINT NOT NULL DEFAULT 0,
  error_code TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON jobs(telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
CREATE TABLE IF NOT EXISTS reports (
  id BIGSERIAL PRIMARY KEY, telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS donations (
  id BIGSERIAL PRIMARY KEY, telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  telegram_charge_id TEXT NOT NULL UNIQUE, currency TEXT NOT NULL, amount BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY, admin_id BIGINT, action TEXT NOT NULL, target TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

async def connect(dsn):
    return await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5, command_timeout=15,
                                     server_settings={"application_name": "telegram-media-bot"})

async def init_db(pool):
    async with pool.acquire() as c:
        await c.execute(SCHEMA)

async def upsert_user(pool, user):
    async with pool.acquire() as c:
        await c.execute("""INSERT INTO users(telegram_id,username,first_name,language_code)
        VALUES($1,$2,$3,$4) ON CONFLICT(telegram_id) DO UPDATE SET username=EXCLUDED.username,
        first_name=EXCLUDED.first_name, language_code=EXCLUDED.language_code,last_active_at=now()""",
        user.id, user.username, user.first_name, user.language_code)

async def banned(pool, user_id):
    async with pool.acquire() as c:
        return bool(await c.fetchval("SELECT is_banned FROM users WHERE telegram_id=$1", user_id))

async def create_job(pool, jid, uid, host, url_hash):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO jobs(id,telegram_id,source_host,url_hash,status) VALUES($1,$2,$3,$4,'queued')",
                         jid, uid, host, url_hash)

async def update_job(pool, jid, status, title=None, fmt=None, size=0, error=None):
    async with pool.acquire() as c:
        await c.execute("""UPDATE jobs SET status=$2,title=COALESCE($3,title),
        selected_format=COALESCE($4,selected_format),bytes_delivered=$5,error_code=$6,
        started_at=CASE WHEN $2='processing' AND started_at IS NULL THEN now() ELSE started_at END,
        finished_at=CASE WHEN $2 IN ('succeeded','failed','cancelled') THEN now() ELSE finished_at END
        WHERE id=$1""", jid, status, title, fmt, size, error)

async def active_for_user(pool, uid):
    async with pool.acquire() as c:
        return await c.fetchval("SELECT count(*) FROM jobs WHERE telegram_id=$1 AND status IN ('queued','processing')", uid)

async def stats(pool, uid):
    async with pool.acquire() as c:
        r = await c.fetchrow("""SELECT count(*) total,
        count(*) FILTER(WHERE status='succeeded') succeeded,
        count(*) FILTER(WHERE status='failed') failed,
        count(*) FILTER(WHERE status='cancelled') cancelled,
        coalesce(sum(bytes_delivered),0) bytes FROM jobs WHERE telegram_id=$1""", uid)
        return dict(r)

async def report(pool, uid, description):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO reports(telegram_id,description) VALUES($1,$2)", uid, description[:1500])

async def set_banned(pool, uid, value):
    async with pool.acquire() as c:
        await c.execute("UPDATE users SET is_banned=$2 WHERE telegram_id=$1", uid, value)


async def claim_channel_invite(pool, user_id):
    # Atomic claim: only the first /start sends the optional channel invitation.
    async with pool.acquire() as c:
        row = await c.fetchrow(
            "UPDATE users SET channel_invite_sent_at=now() "
            "WHERE telegram_id=$1 AND channel_invite_sent_at IS NULL RETURNING telegram_id",
            user_id,
        )
        return row is not None
