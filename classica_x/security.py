from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}


def validate_post_url(value: str, *, allow_synthetic_media: bool = False) -> str:
    """Accept only HTTPS URLs for one public post on an approved X host."""
    parsed = urlparse(value.strip())
    local_synthetic = (
        allow_synthetic_media
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost"}
    )
    if not local_synthetic and (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS):
        raise ValueError("Use uma URL HTTPS válida de x.com ou twitter.com.")
    if parsed.username or parsed.password or (parsed.port and not local_synthetic):
        raise ValueError("A URL não pode conter credenciais ou porta.")
    if local_synthetic:
        return parsed.geturl()
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[-2] != "status" or not parts[-1].isdigit():
        raise ValueError("Use o link de uma publicação individual (…/status/ID).")
    return parsed.geturl()


def default_destination() -> Path:
    destination = Path.home() / "Videos" / "Classica X"
    destination.mkdir(parents=True, exist_ok=True)
    return destination.resolve()


def safe_destination(folder: str) -> Path:
    destination = Path(folder).expanduser().resolve()
    default = (Path.home() / "Videos" / "Classica X").resolve()
    if destination == default:
        destination.mkdir(parents=True, exist_ok=True)
        return destination
    if not destination.is_dir():
        raise ValueError("A pasta de destino não existe.")
    return destination


def safe_filename(name: str) -> str:
    clean = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name).strip(" .")
    return (clean or "video")[:120]
