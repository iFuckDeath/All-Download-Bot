import asyncio, logging, shutil, tempfile, uuid
from pathlib import Path
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from . import db
from .downloader import DownloadError, metadata, formats_for, download
from .keyboards import home, formats
from .security import validate_url, host_of, url_hash

log = logging.getLogger(__name__)
router = Router()

def pretty_bytes(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def duration(n):
    if not n: return "Unknown"
    n = int(n)
    return f"{n//3600}:{(n%3600)//60:02d}:{n%60:02d}" if n >= 3600 else f"{n//60}:{n%60:02d}"

def setup(settings, pool):
    tasks = {}
    semaphore = asyncio.Semaphore(settings.max_active)
    async def guard(message):
        await db.upsert_user(pool, message.from_user)
        if await db.banned(pool, message.from_user.id):
            await message.answer("⛔ Your access is disabled.")
            return False
        return True

    @router.message(CommandStart())
    async def start(m: Message):
        if not await guard(m): return
        await m.answer("✨ <b>MEDIA FLOW</b>\n<i>Your media, made simple.</i>\n\nSend a supported public media URL, then choose an available format.\n\nOnly download media you are authorized to save.", reply_markup=home(settings.custom_emoji_id))
        if settings.channel:
            await m.answer(f"🌍 Updates: @{settings.channel}\nJoining is optional.", reply_markup=__import__("aiogram").types.InlineKeyboardMarkup(inline_keyboard=[[
                __import__("aiogram").types.InlineKeyboardButton(text="📣 Open channel", url=f"https://t.me/{settings.channel}")
            ]]))

    @router.message(Command("help"))
    async def help_cmd(m):
        if await guard(m):
            await m.answer("<b>Commands</b>\n/start — main menu\n/help — help\n/platforms — supported source guidance\n/stats — your usage\n/cancel — cancel active downloads\n/report TEXT — report a problem\n/ping — service status\n/about — bot information")

    @router.message(Command("platforms"))
    async def platforms(m):
        if await guard(m):
            await m.answer("🌐 The bot uses yt-dlp extractors for many public media URLs. Coverage changes and not every link works. Adult sites may work when the content is lawful and accessible without bypassing restrictions. No DRM, paywall, login, age-check or access-control bypass.")

    @router.message(Command("about"))
    async def about(m):
        if await guard(m): await m.answer("✨ <b>Media Flow</b> — a Telegram-only media utility. No website frontend.")

    @router.message(Command("ping"))
    async def ping(m):
        if await guard(m): await m.answer("🟢 Bot process is responding.")

    @router.message(Command("stats"))
    async def stats_cmd(m):
        if not await guard(m): return
        s = await db.stats(pool, m.from_user.id)
        await m.answer(f"📊 <b>Your activity</b>\n\nRequests: <b>{s['count']}</b>\nSuccessful: <b>{s['succeeded']}</b>\nFailed: <b>{s['failed']}</b>\nCancelled: <b>{s['cancelled']}</b>\nDelivered: <b>{pretty_bytes(s['bytes'])}</b>")

    @router.message(Command("cancel"))
    async def cancel(m):
        if not await guard(m): return
        owned = [task for key, task in tasks.items() if key.startswith(f"{m.from_user.id}:") and not task.done()]
        if not owned:
            await m.answer("Nothing is running right now.")
        else:
            for task in owned: task.cancel()
            await m.answer("🛑 Cancellation requested.")

    @router.message(Command("report"))
    async def report_cmd(m):
        if not await guard(m): return
        desc = (m.text or "").partition(" ")[2].strip()
        if not desc:
            await m.answer("Use /report followed by a short description.")
            return
        await db.report(pool, m.from_user.id, desc)
        await m.answer("✅ Report saved. Thank you.")

    @router.message(F.text)
    async def url_message(m):
        if not await guard(m): return
        url = (m.text or "").strip()
        if not url.startswith(("https://", "http://")):
            await m.answer("Send a public HTTP(S) media-page URL to begin.")
            return
        valid, why = await validate_url(url, settings.max_url_length)
        if not valid:
            await m.answer(f"⚠️ {why}")
            return
        if await db.active_for_user(pool, m.from_user.id) >= settings.max_per_user:
            await m.answer("⏳ You already have an active job. Wait or use /cancel.")
            return
        status = await m.answer("🔎 <b>Checking media…</b>")
        try:
            meta = await asyncio.wait_for(metadata(url), timeout=min(settings.timeout, 45))
        except (DownloadError, asyncio.TimeoutError) as e:
            await status.edit_text(f"⚠️ Could not read this URL.\n{e if isinstance(e, DownloadError) else 'Metadata check timed out.'}")
            return
        if meta["playlist"]:
            await status.edit_text("📚 Playlist detected. Batch playlist processing is planned for a later stage; please send an individual item URL for now.")
            return
        jid = uuid.uuid4()
        await db.create_job(pool, jid, m.from_user.id, host_of(url), url_hash(url))
        await db.update_job(pool, jid, "queued", title=meta["title"])
        options = formats_for(meta)
        tasks[f"meta:{jid}"] = {"url": url, "options": options, "user": m.from_user.id, "chat": m.chat.id, "message_id": status.message_id}
        await status.edit_text(f"🎞️ <b>{meta['title']}</b>\n👤 {meta['uploader']}\n⏱️ {duration(meta['duration'])}\n🌐 {meta['extractor']}\n\nChoose an available option:", reply_markup=formats(str(jid), options, settings.custom_emoji_id))

    @router.callback_query(F.data.startswith("home:"))
    async def home_cb(c):
        await c.answer()
        action = c.data.split(":", 1)[1]
        if action == "download": await c.message.answer("📎 Send the media URL in your next message.")
        elif action == "stats":
            s = await db.stats(pool, c.from_user.id)
            await c.message.answer(f"📊 Requests: {s['count']} · Successful: {s['succeeded']} · Failed: {s['failed']}")
        elif action == "sources": await c.message.answer("Send a supported public HTTP(S) media URL. Source support varies.")
        else: await c.message.answer("Send a URL, select a format, and use /cancel to stop a running job.")

    @router.callback_query(F.data.startswith("cancel:"))
    async def cancel_cb(c):
        await c.answer()
        try: jid = uuid.UUID(c.data.split(":", 1)[1])
        except Exception: return
        info = tasks.get(f"meta:{jid}")
        if info and info["user"] == c.from_user.id:
            tasks.pop(f"meta:{jid}", None)
            await db.update_job(pool, jid, "cancelled", error="cancelled")
            await c.message.edit_text("🛑 Selection cancelled.")
            return
        for key, task in list(tasks.items()):
            if key.startswith(f"{c.from_user.id}:{jid}") and not task.done():
                task.cancel()

    @router.callback_query(F.data.startswith("fmt:"))
    async def format_cb(c):
        await c.answer()
        try:
            _, jid_text, index_text = c.data.split(":")
            jid, index = uuid.UUID(jid_text), int(index_text)
        except Exception:
            await c.message.answer("Invalid or expired button.")
            return
        info = tasks.get(f"meta:{jid}")
        if not info or info["user"] != c.from_user.id:
            await c.message.answer("This selection expired. Send the URL again.")
            return
        if sum(not t.done() for k,t in tasks.items() if not k.startswith("meta:")) >= settings.max_active:
            await c.message.answer("⏳ The bot is busy. Try again shortly.")
            return
        if index < 0 or index >= len(info["options"]):
            await c.message.answer("Format unavailable.")
            return
        choice = info["options"][index]
        await db.update_job(pool, jid, "processing", fmt=choice["selector"])
        key = f"{c.from_user.id}:{jid}"
        tasks[key] = asyncio.create_task(run_job(c, info, jid, choice, key))

    async def run_job(c, info, jid, choice, key):
        workdir = Path(tempfile.mkdtemp(prefix=f"{jid}-", dir=settings.temp_dir))
        try:
            await c.message.edit_text(f"⏳ <b>Preparing download</b>\n{choice['label']}")
            async with semaphore:
                result = await download(info["url"], str(workdir), choice["selector"], settings.max_bytes, settings.timeout)
            await c.message.edit_text(f"📤 <b>Sending to Telegram…</b>\n{result['title']}\n{pretty_bytes(result['size'])}")
            try:
                await c.bot.send_document(info["chat"], FSInputFile(result["path"]), caption=f"✅ <b>{result['title']}</b>\n📦 {pretty_bytes(result['size'])}")
            except TelegramBadRequest:
                if Path(result["path"]).suffix.lower() != ".mp4": raise
                await c.bot.send_video(info["chat"], FSInputFile(result["path"]), caption=f"✅ <b>{result['title']}</b>")
            await db.update_job(pool, jid, "succeeded", title=result["title"], size=result["size"])
            await c.message.edit_text("✅ <b>Download complete</b>\nYour file was sent in this chat.")
        except asyncio.CancelledError:
            await db.update_job(pool, jid, "cancelled", error="cancelled")
            try: await c.message.edit_text("🛑 Download cancelled.")
            except Exception: pass
            raise
        except DownloadError as e:
            await db.update_job(pool, jid, "failed", error=e.code)
            try: await c.message.edit_text(f"⚠️ <b>Download failed</b>\n{e}")
            except Exception: pass
        except Exception:
            log.exception("Job failed: %s", jid)
            await db.update_job(pool, jid, "failed", error="internal_error")
            try: await c.message.edit_text("⚠️ Something went wrong. Try another supported URL later.")
            except Exception: pass
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
            tasks.pop(key, None)
            tasks.pop(f"meta:{jid}", None)

    @router.message(Command("admin"))
    async def admin(m):
        if m.from_user.id not in settings.admins:
            await m.answer("⛔ Admin only.")
            return
        await m.answer("<b>Admin commands</b>\n/health\n/users\n/ban USER_ID\n/unban USER_ID")

    @router.message(Command("health"))
    async def health(m):
        if m.from_user.id not in settings.admins: return
        try:
            async with pool.acquire() as conn: await conn.fetchval("SELECT 1")
            await m.answer("🟢 Bot and database are responding.")
        except Exception:
            await m.answer("🔴 Database check failed.")
            log.exception("Health check failed")

    @router.message(Command("users"))
    async def users(m):
        if m.from_user.id not in settings.admins: return
        async with pool.acquire() as conn: n = await conn.fetchval("SELECT count(*) FROM users")
        await m.answer(f"👥 Registered users: <b>{n}</b>")

    @router.message(Command("ban"))
    async def ban(m):
        if m.from_user.id not in settings.admins: return
        parts = (m.text or "").split()
        if len(parts) != 2 or not parts[1].isdigit():
            await m.answer("Use /ban USER_ID"); return
        await db.set_banned(pool, int(parts[1]), True)
        await m.answer("⛔ User banned.")

    @router.message(Command("unban"))
    async def unban(m):
        if m.from_user.id not in settings.admins: return
        parts = (m.text or "").split()
        if len(parts) != 2 or not parts[1].isdigit():
            await m.answer("Use /unban USER_ID"); return
        await db.set_banned(pool, int(parts[1]), False)
        await m.answer("✅ User unbanned.")

    return router
