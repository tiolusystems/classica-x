from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

from .security import safe_destination, safe_filename, validate_post_url
from .store import load, save


class DownloadService:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._cancelled = False
        self._lock = threading.Lock()
        self.state = {"status": "pronto", "message": "", "progress": 0, "preview": None}

    def preview(self, url: str) -> dict:
        url = validate_post_url(url)
        result = subprocess.run(["yt-dlp", "--no-playlist", "--skip-download", "--dump-single-json", url],
                                capture_output=True, text=True, timeout=45, check=False)
        if result.returncode:
            raise ValueError("Não foi possível obter a prévia da publicação pública.")
        info = json.loads(result.stdout)
        entries = info.get("entries") or []
        media_count = len(entries) if entries else 1
        if media_count != 1:
            raise ValueError("Esta publicação possui múltiplas mídias; selecione uma publicação com um único vídeo.")
        chosen = entries[0] if entries else info
        preview = {"title": safe_filename(chosen.get("title") or "Vídeo do X"),
                   "duration": chosen.get("duration"), "thumbnail": chosen.get("thumbnail"), "url": url}
        self.state["preview"] = preview
        return preview

    def start(self, url: str, destination: str, authorized: bool) -> None:
        if not authorized:
            raise ValueError("Confirme que você possui autorização ou fundamento legal antes de baixar.")
        url = validate_post_url(url)
        output_dir = safe_destination(destination)
        with self._lock:
            if self._process and self._process.poll() is None:
                raise ValueError("Já existe um download em andamento.")
            self._cancelled = False
            self.state.update(status="baixando", message="Iniciando download…", progress=0)
            threading.Thread(target=self._run, args=(url, output_dir), daemon=True).start()

    def _run(self, url: str, output_dir: Path) -> None:
        template = str(output_dir / "%(title).120B [%(id)s].%(ext)s")
        command = ["yt-dlp", "--ignore-config", "--no-playlist", "--restrict-filenames", "--newline",
                   "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", template, url]
        try:
            with self._lock:
                options = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                           "text": True, "encoding": "utf-8", "errors": "replace"}
                if os.name == "nt":
                    options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
                else:
                    options["start_new_session"] = True
                self._process = subprocess.Popen(command, **options)
                process = self._process
            for line in process.stdout or []:
                if "[download]" in line:
                    self.state["message"] = line.strip()[-180:]
                    import re
                    found = re.search(r"(\d{1,3}(?:\.\d+)?)%", line)
                    if found:
                        self.state["progress"] = float(found.group(1))
            if process.wait() != 0 and self._cancelled:
                return
            if process.returncode != 0:
                raise RuntimeError("O extrator não concluiu o download. Confira se a publicação é pública e acessível.")
            recent = max((p for p in output_dir.glob("*") if p.is_file()), key=lambda p: p.stat().st_mtime, default=None)
            valid, has_audio = self._inspect_media(recent) if recent else (False, False)
            if not valid:
                raise RuntimeError("O arquivo final não passou na validação FFprobe.")
            history = load("history.json", [])
            history.insert(0, {"url": url, "file": str(recent), "at": int(time.time())})
            save("history.json", history[:100])
            suffix = " (vídeo sem áudio)" if not has_audio else ""
            self.state.update(status="concluído", progress=100, message=f"{recent}{suffix}")
        except Exception as exc:
            self.state.update(status="erro", message=str(exc))
        finally:
            with self._lock:
                self._process = None

    @staticmethod
    def _inspect_media(file: Path) -> tuple[bool, bool]:
        if not file.is_file() or file.stat().st_size == 0 or not shutil.which("ffprobe"):
            return False, False
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(file)],
                               capture_output=True, text=True, timeout=20, check=False)
        if probe.returncode != 0:
            return False, False
        try:
            info = json.loads(probe.stdout)
            kinds = {stream.get("codec_type") for stream in info.get("streams", [])}
            return bool(info.get("format", {}).get("duration")) and "video" in kinds, "audio" in kinds
        except json.JSONDecodeError:
            return False, False

    def cancel(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._cancelled = True
                if os.name == "nt":
                    subprocess.run(["taskkill", "/pid", str(self._process.pid), "/t", "/f"],
                                   capture_output=True, check=False)
                else:
                    os.killpg(self._process.pid, signal.SIGTERM)
                self.state.update(status="cancelado", message="Download cancelado pelo usuário.")
