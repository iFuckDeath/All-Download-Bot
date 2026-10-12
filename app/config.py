import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def positive_int(name, default):
    try:
        n = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if n < 1:
        raise RuntimeError(f"{name} must be >= 1")
    return n

@dataclass(frozen=True)
class Settings:
    token: str
    database_url: str
    admins: frozenset[int]
    max_active: int
    max_per_user: int
    max_bytes: int
    timeout: int
    max_url_length: int
    temp_dir: Path
    log_level: str
    channel: str
    custom_emoji_id: str

def load_settings():
    token = os.getenv("BOT_TOKEN", "").strip()
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required")
    if not dsn.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL")
    try:
        admins = frozenset(int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip())
    except ValueError as exc:
        raise RuntimeError("ADMIN_IDS must contain numeric Telegram IDs") from exc
    if not admins:
        raise RuntimeError("Set at least one numeric Telegram ID in ADMIN_IDS")
    temp = Path(os.getenv("TEMP_DIR", "/tmp/telegram-media-bot"))
    temp.mkdir(parents=True, exist_ok=True)
    return Settings(token, dsn, admins, positive_int("MAX_ACTIVE_JOBS", 2),
                    positive_int("MAX_JOBS_PER_USER", 1), positive_int("MAX_FILE_BYTES", 51380224),
                    positive_int("JOB_TIMEOUT_SECONDS", 300), positive_int("MAX_URL_LENGTH", 2048),
                    temp, os.getenv("LOG_LEVEL", "INFO").upper(),
                    os.getenv("CHANNEL_USERNAME", "TheEarthX").lstrip("@"),
                    os.getenv("CUSTOM_EMOJI_ID", "").strip())
