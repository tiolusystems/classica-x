"""The same independent X engine can render inside the Clássica tab without a second browser."""
import json
from pathlib import Path

from classica_x import app


def test_embedded_session_avoids_browser_and_writes_one_time_handshake(monkeypatch, tmp_path):
    ready = tmp_path / "embedded-ready.json"
    class StubService:
        def shutdown(self): pass
    class StubServer:
        server_port = 39415
        session_token = "non-production-test-token"
        service = StubService()
        def serve_forever(self): pass
        def server_close(self): pass

    monkeypatch.setenv("CLASSICA_X_EMBED_READY_FILE", str(ready))
    monkeypatch.delenv("CLASSICA_X_SMOKE_READY_FILE", raising=False)
    monkeypatch.setattr(app, "create_server", lambda **kwargs: StubServer())
    monkeypatch.setattr(app.webbrowser, "open", lambda *args: (_ for _ in ()).throw(AssertionError("Opened another browser")))
    app.main()
    assert json.loads(ready.read_text(encoding="utf-8")) == {
        "port": 39415, "session": "non-production-test-token"
    }
    assert not ready.with_suffix(".tmp").exists()
