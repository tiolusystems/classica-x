from __future__ import annotations

import hmac
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .security import safe_destination
from .service import DownloadService
from .store import load, save

WEB = Path(__file__).parent / "web"


def create_server(port: int = 0, service: DownloadService | None = None,
                  session_token: str | None = None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.service = service or DownloadService()
    server.session_token = session_token or secrets.token_urlsafe(32)
    return server


class Handler(BaseHTTPRequestHandler):
    server: ThreadingHTTPServer

    def log_message(self, *_):
        pass

    @property
    def _origin(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def _json(self, code: int, value: dict | list) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _authorize_api(self, require_origin: bool = False) -> bool:
        expected_host = f"127.0.0.1:{self.server.server_port}"
        if not hmac.compare_digest(self.headers.get("Host", ""), expected_host):
            self._json(400, {"error": "Host local inválido."})
            return False
        token = self.headers.get("X-Classica-Session", "")
        if not hmac.compare_digest(token, self.server.session_token):
            self._json(401, {"error": "Sessão local não autorizada."})
            return False
        if require_origin and not hmac.compare_digest(self.headers.get("Origin", ""), self._origin):
            self._json(403, {"error": "Origem local inválida."})
            return False
        return True

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError as exc:
            raise ValueError("Corpo da requisição inválido.") from exc
        if length < 1 or length > 10_000:
            raise ValueError("Corpo da requisição inválido.")
        try:
            data = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise ValueError("JSON inválido.") from exc
        if not isinstance(data, dict):
            raise ValueError("JSON inválido.")
        return data

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            if not self._authorize_api():
                return
            if path == "/api/state":
                return self._json(200, self.server.service.snapshot())
            if path == "/api/history":
                return self._json(200, load("history.json", []))
            if path == "/api/settings":
                return self._json(200, load("settings.json", {"destination": str(Path.home() / "Videos" / "Classica X")}))
            return self._json(404, {"error": "Rota não encontrada."})
        file = WEB / ("index.html" if path == "/" else path.lstrip("/"))
        if file.is_file() and file.resolve().is_relative_to(WEB.resolve()):
            content = file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/") or not self._authorize_api(require_origin=True):
            return
        try:
            data = self._read_json()
            if path == "/api/preview":
                return self._json(200, self.server.service.preview(data["url"]))
            if path == "/api/download":
                self.server.service.start(data["url"], data["destination"], bool(data.get("authorized")))
                return self._json(202, self.server.service.snapshot())
            if path == "/api/cancel":
                self.server.service.cancel()
                return self._json(200, self.server.service.snapshot())
            if path == "/api/settings":
                save("settings.json", {"destination": str(safe_destination(data["destination"]))})
                return self._json(200, {"ok": True})
            return self._json(404, {"error": "Rota não encontrada."})
        except (KeyError, ValueError) as exc:
            self._json(400, {"error": str(exc)})


def main() -> None:
    server = create_server()
    # The fragment never travels in the HTTP request or browser history.
    url = f"http://127.0.0.1:{server.server_port}/#session={server.session_token}"
    threading.Timer(.15, webbrowser.open, args=(url,)).start()
    print(f"Clássica X em http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    finally:
        server.service.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
