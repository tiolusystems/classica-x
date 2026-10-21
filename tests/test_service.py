import json
import os
from pathlib import Path

from classica_x.service import DownloadService


def test_extractor_commands_ignore_user_configuration(tmp_path):
    assert "--ignore-config" in DownloadService._command("https://x.com/user/status/1", tmp_path)


def test_final_path_must_be_reported_inside_destination(tmp_path):
    media = tmp_path / "done.mp4"; media.write_bytes(b"content")
    assert DownloadService._reported_file([str(media)], tmp_path) == media
    try:
        DownloadService._reported_file(["C:/outside.mp4"], tmp_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("accepted unreported destination")


def test_frozen_runtime_uses_internal_ffprobe_and_path(monkeypatch, tmp_path):
    monkeypatch.setattr("classica_x.service.sys.frozen", True, raising=False)
    executable = tmp_path / "ClassicaX.exe"
    monkeypatch.setattr("classica_x.service.sys.executable", str(executable))
    assert DownloadService._tool("yt-dlp") == str(tmp_path / "ClassicaXExtractor.exe")
    assert DownloadService._tool("ffprobe") == str(tmp_path / "_internal" / "ffprobe.exe")
    path_parts = DownloadService._environment()["PATH"].split(os.pathsep)
    assert path_parts[:2] == [str(tmp_path), str(tmp_path / "_internal")]


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
