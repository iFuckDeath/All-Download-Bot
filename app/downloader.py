import asyncio
from pathlib import Path
import yt_dlp

class DownloadError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def _extract(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

async def metadata(url):
    try:
        info = await asyncio.to_thread(_extract, url, {"quiet": True, "no_warnings": True,
          "noplaylist": True, "skip_download": True, "socket_timeout": 12, "retries": 1})
        if not info:
            raise DownloadError("unavailable", "No media metadata was returned.")
        formats = []
        for f in info.get("formats", []):
            if f.get("format_id"):
                formats.append({"height": f.get("height"), "vcodec": f.get("vcodec"),
                                "acodec": f.get("acodec"), "filesize": f.get("filesize") or f.get("filesize_approx")})
        return {"title": str(info.get("title") or "Untitled")[:240],
                "uploader": str(info.get("uploader") or info.get("channel") or "Unknown creator")[:100],
                "duration": info.get("duration"), "extractor": str(info.get("extractor_key") or "Source")[:80],
                "playlist": info.get("_type") in {"playlist", "multi_video"}, "formats": formats}
    except DownloadError:
        raise
    except Exception as exc:
        low = str(exc).lower()
        if "unsupported url" in low or "no suitable extractor" in low:
            raise DownloadError("unsupported", "This source is not supported by the installed extractor.")
        if any(x in low for x in ("login", "sign in", "private video", "age verification")):
            raise DownloadError("restricted", "This media requires access or verification that the bot does not bypass.")
        if "429" in low or "rate limit" in low:
            raise DownloadError("rate_limited", "The source is rate-limiting requests. Try again later.")
        raise DownloadError("unavailable", "Media could not be read; it may be unavailable or restricted.")

def formats_for(meta):
    out = []
    for h in (1080, 720, 480, 360):
        if any(f["height"] and f["height"] >= h and f["vcodec"] != "none" for f in meta["formats"]):
            out.append({"label": f"🎬 {h}p", "selector": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"})
    if any(f["acodec"] not in (None, "none") for f in meta["formats"]):
        out.append({"label": "🎵 Audio", "selector": "bestaudio/best"})
    return out or [{"label": "⬇️ Best available", "selector": "best"}]

def _download(url, folder, selector, cap):
    template = str(Path(folder) / "%(id)s.%(ext)s")
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "outtmpl": template,
            "format": selector, "merge_output_format": "mp4", "restrictfilenames": True,
            "socket_timeout": 15, "retries": 1, "fragment_retries": 1, "max_filesize": cap}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        files = [p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in
                 {".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".opus", ".ogg", ".wav"}]
        if not files:
            raise DownloadError("empty_result", "No supported media file was produced.")
        target = max(files, key=lambda p: p.stat().st_size)
        size = target.stat().st_size
        if size > cap:
            target.unlink(missing_ok=True)
            raise DownloadError("too_large", "The file exceeds the configured Telegram upload cap.")
        return {"path": str(target), "title": str(info.get("title") or target.stem)[:240], "size": size}

async def download(url, folder, selector, cap, timeout):
    try:
        return await asyncio.wait_for(asyncio.to_thread(_download, url, folder, selector, cap), timeout=timeout)
    except asyncio.TimeoutError:
        raise DownloadError("timeout", "The download exceeded its time limit.")
    except DownloadError:
        raise
    except Exception as exc:
        low = str(exc).lower()
        if "drm" in low or "protected" in low:
            raise DownloadError("restricted", "Protected media cannot be downloaded.")
        if "maximum file size" in low or "too large" in low:
            raise DownloadError("too_large", "The file exceeds the configured limit.")
        raise DownloadError("download_failed", "Download failed. The source may be unavailable or may restrict downloading.")
