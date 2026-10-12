import asyncio, hashlib, ipaddress, socket
from urllib.parse import urlparse

async def validate_url(url, max_length=2048):
    if not url or len(url) > max_length:
        return False, "The URL is empty or too long."
    try:
        p = urlparse(url.strip())
        if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
            return False, "Only valid public HTTP(S) URLs are supported."
        host = p.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local")):
            return False, "Local/private URLs are not supported."
        try:
            ip = ipaddress.ip_address(host)
            if not ip.is_global:
                return False, "Private or reserved IP addresses are not supported."
        except ValueError:
            pass
        records = await asyncio.get_running_loop().getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        if not records:
            return False, "The hostname could not be resolved."
        for rec in records:
            if not ipaddress.ip_address(rec[4][0]).is_global:
                return False, "The hostname resolves to a private or reserved address."
        return True, ""
    except (ValueError, OSError, socket.gaierror):
        return False, "Could not validate this URL. Check the address and try again."

def host_of(url):
    return (urlparse(url).hostname or "unknown").lower()[:253]

def url_hash(url):
    return hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()
