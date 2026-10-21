from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .security import safe_destination, safe_filename, validate_post_url
from .store import load, save


class DownloadService:
    def __init__(self):
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._worker: threading.Thread | None = None
        self._cancel_event: threading.Event | None = None
        self._job_id = 0
        self.state = {"status": "pronto", "message": "", "progress": 0, "preview": None}

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.state)

    def preview(self, url: str) -> dict:
        url = validate_post_url(url)
        result = subprocess.run([self._tool("yt-dlp"), "--ignore-config", "--no-playlist", "--skip-download", "--dump-single-json", url],
                                capture_output=True, text=True, timeout=45, check=False, env=self._environment())
        if result.returncode:
            raise ValueError("Não foi possível obter a prévia da publicação pública.")
        info = json.loads(result.stdout)
        entries = info.get("entries") or []
        if len(entries) > 1:
            raise ValueError("Esta publicação possui múltiplas mídias; selecione uma publicação com um único vídeo.")
        chosen = entries[0] if entries else info
        preview = {"title": safe_filename(chosen.get("title") or "Vídeo do X"),
                   "duration": chosen.get("duration"), "thumbnail": chosen.get("thumbnail"), "url": url}
        with self._lock:
            self.state["preview"] = preview
        return preview

    def start(self, url: str, destination: str, authorized: bool) -> None:
        if not authorized:
            raise ValueError("Confirme que você possui autorização ou fundamento legal antes de baixar.")
        url, output_dir = validate_post_url(url), safe_destination(destination)
        with self._lock:
            if self._worker and self._worker.is_alive():
                raise ValueError("Já existe um download em andamento.")
            self._job_id += 1
            job_id, cancelled = self._job_id, threading.Event()
            self._cancel_event = cancelled
            self._process = None
            self.state.update(status="baixando", message="Iniciando download…", progress=0)
            self._worker = threading.Thread(target=self._run, args=(job_id, cancelled, url, output_dir), daemon=True)
            self._worker.start()

    def _current(self, job_id: int) -> bool:
        return job_id == self._job_id

    def _set_state(self, job_id: int, **updates) -> None:
        with self._lock:
            if self._current(job_id):
                self.state.update(**updates)

    @staticmethod
    def _command(url: str, output_dir: Path) -> list[str]:
        template = str(output_dir / "%(title).120B [%(id)s].%(ext)s")
        return [DownloadService._tool("yt-dlp"), "--ignore-config", "--no-playlist", "--restrict-filenames", "--newline",
                "--print", "after_move:filepath", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", template, url]

    def _run(self, job_id: int, cancelled: threading.Event, url: str, output_dir: Path) -> None:
        process: subprocess.Popen | None = None
        lines: list[str] = []
        try:
            if cancelled.is_set():
                return
            options = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True,
                       "encoding": "utf-8", "errors": "replace", "env": self._environment()}
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                options["start_new_session"] = True
            process = subprocess.Popen(self._command(url, output_dir), **options)
            with self._lock:
                if not self._current(job_id) or cancelled.is_set():
                    self._terminate(process)
                    return
                self._process = process
            for line in process.stdout or []:
                lines.append(line.strip())
                found = re.search(r"(\d{1,3}(?:\.\d+)?)%", line)
                if found:
                    self._set_state(job_id, message=line.strip()[-180:], progress=float(found.group(1)))
                if cancelled.is_set():
                    self._terminate(process)
                    break
            returncode = process.wait()
            if cancelled.is_set():
                self._set_state(job_id, status="cancelado", message="Download cancelado pelo usuário.")
                return
            if returncode != 0:
                raise RuntimeError("O extrator não concluiu o download. Confira se a publicação é pública e acessível.")
            final_path = self._reported_file(lines, output_dir)
            valid, has_audio = self._inspect_media(final_path)
            if not valid:
                raise RuntimeError("O arquivo final não passou na validação FFprobe.")
            history = load("history.json", [])
            history.insert(0, {"url": url, "file": str(final_path), "at": int(time.time())})
            save("history.json", history[:100])
            suffix = " (vídeo sem áudio)" if not has_audio else ""
            self._set_state(job_id, status="concluído", progress=100, message=f"{final_path}{suffix}")
        except Exception as exc:
            if not cancelled.is_set():
                self._set_state(job_id, status="erro", message=str(exc))
        finally:
            with self._lock:
                if self._current(job_id) and self._process is process:
                    self._process = None

    @staticmethod
    def _reported_file(lines: list[str], output_dir: Path) -> Path:
        for line in reversed(lines):
            candidate = Path(line)
            try:
                candidate.resolve().relative_to(output_dir.resolve())
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
        raise RuntimeError("O extrator não retornou o caminho do arquivo final.")

    @staticmethod
    def _tool(name: str) -> str:
        if getattr(sys, "frozen", False):
            packaged = {"yt-dlp": "ClassicaXExtractor.exe", "ffprobe": "ffprobe.exe"}[name]
            return str(Path(sys.executable).parent / packaged)
        return name

    @staticmethod
    def _environment() -> dict[str, str]:
        environment = os.environ.copy()
        if getattr(sys, "frozen", False):
            folder = str(Path(sys.executable).parent)
            environment["PATH"] = folder + os.pathsep + environment.get("PATH", "")
        return environment

    @staticmethod
    def _inspect_media(file: Path) -> tuple[bool, bool]:
        probe_tool = DownloadService._tool("ffprobe")
        if not file.is_file() or file.stat().st_size == 0 or (not getattr(sys, "frozen", False) and not shutil.which(probe_tool)):
            return False, False
        probe = subprocess.run([probe_tool, "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(file)],
                               capture_output=True, text=True, timeout=20, check=False)
        if probe.returncode != 0:
            return False, False
        try:
            info = json.loads(probe.stdout)
            kinds = {stream.get("codec_type") for stream in info.get("streams", [])}
            return bool(info.get("format", {}).get("duration")) and "video" in kinds, "audio" in kinds
        except json.JSONDecodeError:
            return False, False

    @staticmethod
    def _terminate(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/pid", str(process.pid), "/t", "/f"], capture_output=True, check=False)
        else:
            os.killpg(process.pid, signal.SIGTERM)

    def cancel(self) -> None:
        with self._lock:
            if not self._worker or not self._worker.is_alive() or not self._cancel_event:
                return
            self._cancel_event.set()
            if self._process:
                self._terminate(self._process)

    def shutdown(self, timeout: float = 5) -> None:
        self.cancel()
        with self._lock:
            worker = self._worker
        if worker:
            worker.join(timeout)
