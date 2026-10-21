from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}


def validate_post_url(value: str) -> str:
    """Accept only HTTPS URLs for one public post on an approved X host."""
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Use uma URL HTTPS válida de x.com ou twitter.com.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[-2] != "status" or not parts[-1].isdigit():
        raise ValueError("Use o link de uma publicação individual (…/status/ID).")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("A URL não pode conter credenciais ou porta.")
    return parsed.geturl()


def safe_destination(folder: str) -> Path:
    destination = Path(folder).expanduser().resolve()
    if not destination.is_dir():
        raise ValueError("A pasta de destino não existe.")
    return destination


def safe_filename(name: str) -> str:
    clean = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name).strip(" .")
    return (clean or "video")[:120]
