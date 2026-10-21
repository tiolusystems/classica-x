import json
from pathlib import Path

from classica_x.service import DownloadService


def test_ffprobe_accepts_video_without_audio(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"content")
    monkeypatch.setattr("classica_x.service.shutil.which", lambda _: "ffprobe")
    class Result:
        returncode = 0
        stdout = json.dumps({"format": {"duration": "5.0"}, "streams": [{"codec_type": "video"}]})
    monkeypatch.setattr("classica_x.service.subprocess.run", lambda *args, **kwargs: Result())
    assert DownloadService._inspect_media(media) == (True, False)


def test_ffprobe_rejects_non_video(monkeypatch, tmp_path):
    media = tmp_path / "audio.mp4"
    media.write_bytes(b"content")
    monkeypatch.setattr("classica_x.service.shutil.which", lambda _: "ffprobe")
    class Result:
        returncode = 0
        stdout = json.dumps({"format": {"duration": "5.0"}, "streams": [{"codec_type": "audio"}]})
    monkeypatch.setattr("classica_x.service.subprocess.run", lambda *args, **kwargs: Result())
    assert DownloadService._inspect_media(media) == (False, True)
