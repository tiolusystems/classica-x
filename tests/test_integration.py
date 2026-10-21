import functools
import http.server
import shutil
import subprocess
import sys
import threading

import pytest

from classica_x.service import DownloadService


@pytest.mark.integration
def test_ytdlp_and_ffprobe_with_synthetic_media(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg não está disponível")
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=160x90:r=10", "-f", "lavfi", "-i", "sine=frequency=1000", "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", str(source)], check=True, capture_output=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        output = tmp_path / "download.mp4"
        subprocess.run([sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist", "-o", str(output), f"http://127.0.0.1:{server.server_port}/source.mp4"], check=True, capture_output=True)
        assert DownloadService._inspect_media(output) == (True, True)
    finally:
        server.shutdown(); server.server_close(); thread.join()
