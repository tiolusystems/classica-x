from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .service import DownloadService
from .store import load, save

SERVICE = DownloadService()
WEB = Path(__file__).parent.parent / "web"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def _json(self, code, value):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state": return self._json(200, SERVICE.state)
        if path == "/api/history": return self._json(200, load("history.json", []))
        if path == "/api/settings": return self._json(200, load("settings.json", {"destination": str(Path.home() / "Videos" / "Classica X")}))
        file = WEB / ("index.html" if path == "/" else path.lstrip("/"))
        if file.is_file() and file.resolve().parent == WEB.resolve():
            content = file.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(content); return
        self.send_error(404)
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(min(size, 10_000)))
            if self.path == "/api/preview": return self._json(200, SERVICE.preview(data["url"]))
            if self.path == "/api/download": SERVICE.start(data["url"], data["destination"], bool(data.get("authorized"))); return self._json(202, SERVICE.state)
            if self.path == "/api/cancel": SERVICE.cancel(); return self._json(200, SERVICE.state)
            if self.path == "/api/settings": save("settings.json", {"destination": data["destination"]}); return self._json(200, {"ok": True})
            self.send_error(404)
        except (ValueError, KeyError) as exc: self._json(400, {"error": str(exc)})

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}"
    threading.Timer(.15, webbrowser.open, args=(url,)).start()
    print(f"Clássica X em {url}")
    server.serve_forever()

if __name__ == "__main__": main()
