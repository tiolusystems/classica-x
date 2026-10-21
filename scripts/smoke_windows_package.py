from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: object) -> None:
        pass


def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True, **kwargs)


def wait_for_ready(path: Path, process: subprocess.Popen[str]) -> dict[str, object]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise RuntimeError(f"ClassicaX.exe terminou prematuramente ({process.returncode}).")
        time.sleep(.1)
    raise TimeoutError("ClassicaX.exe nao sinalizou inicializacao.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    app = bundle / "ClassicaX.exe"
    extractor = bundle / "ClassicaXExtractor.exe"
    ffmpeg = bundle / "_internal" / "ffmpeg.exe"
    ffprobe = bundle / "_internal" / "ffprobe.exe"
    for component in (app, extractor, ffmpeg, ffprobe):
        if not component.is_file():
            raise FileNotFoundError(component)

    with tempfile.TemporaryDirectory(prefix="classica-x-package-") as temporary:
        root = Path(temporary)
        source = root / "synthetic.avi"
        output_template = root / "converted.%(ext)s"
        run([str(ffmpeg), "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-t", "1", "-c:v", "mpeg4", str(source)])

        handler = lambda *a, **kw: QuietHandler(*a, directory=str(root), **kw)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        ready_file = root / "ready.json"
        environment = os.environ.copy()
        environment["CLASSICA_X_SMOKE_READY_FILE"] = str(ready_file)
        environment["PATH"] = os.pathsep.join((str(bundle), str(bundle / "_internal"), environment.get("PATH", "")))
        application = subprocess.Popen([str(app)], cwd=bundle, env=environment, text=True)
        try:
            ready = wait_for_ready(ready_file, application)
            connection = HTTPConnection("127.0.0.1", int(ready["port"]), timeout=5)
            connection.request("GET", "/api/state", headers={
                "Host": f"127.0.0.1:{ready['port']}",
                "X-Classica-Session": str(ready["session"]),
            })
            response = connection.getresponse()
            response.read()
            connection.close()
            if response.status != 200:
                raise RuntimeError(f"API local retornou {response.status}.")

            url = f"http://127.0.0.1:{httpd.server_port}/{source.name}"
            run([str(extractor), "--ignore-config", "--no-playlist", "--recode-video", "mp4", "-o", str(output_template), url], cwd=bundle, env=environment)
            outputs = list(root.glob("converted*.mp4"))
            if len(outputs) != 1 or outputs[0].stat().st_size == 0:
                raise RuntimeError("Conversao nao produziu um MP4 valido.")
            probe = run([str(ffprobe), "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(outputs[0])])
            if "video" not in probe.stdout:
                raise RuntimeError("FFprobe nao encontrou fluxo de video no arquivo convertido.")
        finally:
            httpd.shutdown()
            application.terminate()
            try:
                application.wait(timeout=10)
            except subprocess.TimeoutExpired:
                application.kill()
                application.wait(timeout=10)

    print("Windows package smoke test passed")


if __name__ == "__main__":
    main()
