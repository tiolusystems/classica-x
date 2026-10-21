"""Guard the independent X UI contract and canonical Clássica identity."""
from html.parser import HTMLParser
from pathlib import Path


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "label":
            self.labels.append(values.get("for"))


def test_x_layout_matches_classica_identity_without_coupling_engines():
    html = (Path(__file__).parents[1] / "classica_x" / "web" / "index.html").read_text(encoding="utf-8")
    parser = Page()
    parser.feed(html)
    assert len(parser.ids) == len(set(parser.ids))
    assert {"url", "destination", "authorized", "download-form", "status-title", "progress", "history-list"} <= set(parser.ids)
    assert {"url", "destination", "authorized"} <= set(parser.labels)
    assert 'aria-label="by ☧ SYSTEMS"' in html
    assert 'by <span aria-hidden="true">☧</span> SYSTEMS' in html
    assert all(token in html for token in ("#f6f2e9", "#fffdf8", "#29352e", "#315747", "#d7c49c"))
    assert "Clássica" in html and "VÍDEOS DO X" in html
    assert "X-Classica-Session" in html
    assert "api('download',data())" in html
    assert "api('cancel',{})" in html
    assert 'javascript:' not in html
    assert '<script src="http' not in html
