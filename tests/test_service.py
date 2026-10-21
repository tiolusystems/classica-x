import json
import os
import threading
from pathlib import Path

from classica_x.service import DownloadService


def test_extractor_commands_ignore_user_configuration(tmp_path):
    command = DownloadService._command("https://x.com/user/status/1", tmp_path)
    assert "--ignore-config" in command
    assert command[command.index("--recode-video") + 1] == "mp4"


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


def test_immediate_cancel_reaches_terminal_state_before_subprocess(monkeypatch, tmp_path):
    class IdleWorker:
        def __init__(self, *args, **kwargs): pass
        def start(self): pass
        def is_alive(self): return True

    service = DownloadService()
    monkeypatch.setattr("classica_x.service.threading.Thread", IdleWorker)
    service.start("https://x.com/user/status/1", str(tmp_path), True)
    cancelled = service._cancel_event
    service.cancel()
    assert service.snapshot()["status"] == "cancelado"
    monkeypatch.setattr("classica_x.service.subprocess.Popen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess started")))
    service._run(1, cancelled, "https://x.com/user/status/1", tmp_path)
    assert service.snapshot()["status"] == "cancelado"


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


def test_real_download_without_after_move_path_uses_only_its_own_mp4(monkeypatch, tmp_path):
    """The exact Windows/X failure: MP4 exists, but yt-dlp printed no final path."""
    previous = tmp_path / "old.mp4"
    previous.write_bytes(b"existing-user-video")
    recorded = []

    class FakeProcess:
        def __init__(self, command, **kwargs):
            output_template = command[command.index("-o") + 1]
            staging = Path(output_template).parent
            assert staging.parent == tmp_path
            assert staging.name.startswith(".classica-x-")
            (staging / "new.mp4").write_bytes(b"new-valid-video")
            self.stdout = iter(["[download] 100% of media", "[VideoConvertor] Done"])
        def wait(self):
            return 0

    monkeypatch.setattr("classica_x.service.subprocess.Popen", FakeProcess)
    monkeypatch.setattr("classica_x.service.DownloadService._inspect_media", lambda path: (True, True))
    monkeypatch.setattr("classica_x.service.load", lambda *_: [])
    monkeypatch.setattr("classica_x.service.save", lambda name, content: recorded.extend(content))
    service = DownloadService()
    service._job_id = 1
    service._run(1, threading.Event(), "https://x.com/u/status/123", tmp_path)
    assert service.snapshot()["status"] == "concluído"
    assert previous.read_bytes() == b"existing-user-video"
    files = sorted(tmp_path.iterdir())
    assert len(files) == 2, files
    final = next(p for p in files if p.name != "old.mp4")
    assert final.name.startswith("new [") and final.suffix == ".mp4"
    assert final.read_bytes() == b"new-valid-video"
    assert recorded[0]["file"] == str(final)


def test_staged_mp4_requires_exactly_one_new_video(tmp_path):
    old = tmp_path / "preexisting.mp4"
    old.write_bytes(b"unrelated")
    staging = tmp_path / ".classica-x-isolated"
    staging.mkdir()
    for filename in ("one.mp4", "two.mp4"):
        (staging / filename).write_bytes(b"possible-video")
    try:
        DownloadService._staged_mp4([str(old)], staging)
    except RuntimeError as error:
        assert "MP4 único" in str(error)
    else:
        raise AssertionError("Two possible outputs were accepted")
    (staging / "two.mp4").unlink()
    assert DownloadService._staged_mp4([], staging).name == "one.mp4"
