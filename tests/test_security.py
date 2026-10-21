import pytest
from classica_x.security import safe_filename, validate_post_url


@pytest.mark.parametrize("url", ["https://x.com/user/status/123", "https://twitter.com/user/status/456?x=1"])
def test_valid_public_post(url):
    assert validate_post_url(url).startswith("https://")


@pytest.mark.parametrize("url", ["http://x.com/a/status/1", "https://evil.test/a/status/1", "https://x.com/a", "https://x.com/a/status/nope"])
def test_rejects_unsafe_or_non_post_url(url):
    with pytest.raises(ValueError): validate_post_url(url)


def test_filename_cannot_escape_path():
    assert "/" not in safe_filename("../../bad:name.mp4")
    assert "\\" not in safe_filename("../../bad:name.mp4")
