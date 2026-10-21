from __future__ import annotations

import json
import os
from pathlib import Path


def data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "ClassicaX"
    root.mkdir(parents=True, exist_ok=True)
    return root


def load(name: str, default):
    file = data_dir() / name
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(name: str, value) -> None:
    file = data_dir() / name
    temporary = file.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(file)
