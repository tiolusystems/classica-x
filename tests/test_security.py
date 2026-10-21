import pytest
from classica_x.security import default_destination, safe_destination, safe_filename, validate_post_url


@pytest.mark.parametrize("url", ["https://x.com/user/status/123", "https://twitter.com/user/status/456?x=1"])
def test_valid_public_post(url):
    assert validate_post_url(url).startswith("https://")


@pytest.mark.parametrize("url", ["http://x.com/a/status/1", "https://evil.test/a/status/1", "https://x.com/a", "https://x.com/a/status/nope"])
def test_rejects_unsafe_or_non_post_url(url):
    with pytest.raises(ValueError): validate_post_url(url)


def test_filename_cannot_escape_path():
    assert "/" not in safe_filename("../../bad:name.mp4")
    assert "\\" not in safe_filename("../../bad:name.mp4")


def test_default_destination_is_created_without_accepting_missing_custom_folder(monkeypatch, tmp_path):
    monkeypatch.setattr("classica_x.security.Path.home", lambda: tmp_path)
    default = default_destination()
    assert default.is_dir()
    assert safe_destination(str(default)) == default
    with pytest.raises(ValueError):
        safe_destination(str(tmp_path / "custom-missing"))


def test_synthetic_media_requires_explicit_test_flag():
    url = "http://127.0.0.1:8765/media.mp4"
    with pytest.raises(ValueError):
        validate_post_url(url)
    assert validate_post_url(url, allow_synthetic_media=True) == url
