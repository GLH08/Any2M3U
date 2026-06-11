from any2m3u.m3u.filters import FileEntry
from any2m3u.m3u.renderer import render_m3u


def entry(entry_id: str, path: str) -> FileEntry:
    return {"path": path, "size": 100, "mtime": 0.0, "etag": None}


def test_render_basic():
    e = entry("abc", "Movies/A.mp4")
    text = render_m3u(
        entries=[e],
        entry_ids=["abc"],
        group_title="Movies",
        logo_lookup=lambda p: None,
        tpl=(
            "#EXTINF:-1 tvg-logo=\"<base>/logo/<sid>/<logo>\" group-title=\"<group>\",<title>\n"
            "<base>/proxy?token=<t>&id=<eid>"
        ),
        base_url="http://x",
        source_id=1,
        token="T",
    )
    assert "#EXTM3U" in text
    assert 'group-title="Movies"' in text
    assert ",A" in text  # title strips extension
    assert "http://x/proxy?token=T&id=abc" in text


def test_render_with_logo():
    text = render_m3u(
        entries=[entry("a", "Movies/A.mp4")],
        entry_ids=["a"],
        group_title="",
        logo_lookup=lambda p: "A.jpg",
        tpl=(
            "#EXTINF:-1 tvg-logo=\"<logo>\" group-title=\"<group>\",<title>\n"
            "<base>/proxy?token=<t>&id=<eid>"
        ),
        base_url="http://x", source_id=1, token="T",
    )
    assert 'tvg-logo="A.jpg"' in text


def test_render_omits_logo_when_missing():
    text = render_m3u(
        entries=[entry("a", "Movies/A.mp4")],
        entry_ids=["a"],
        group_title="",
        logo_lookup=lambda p: None,
        tpl=(
            "#EXTINF:-1 tvg-logo=\"<logo>\" group-title=\"<group>\",<title>\n"
            "<base>/proxy?token=<t>&id=<eid>"
        ),
        base_url="http://x", source_id=1, token="T",
    )
    # Logo attribute should be removed entirely (not left as tvg-logo="")
    lines = text.split("\n")
    # line 0 is #EXTM3U, line 1 is the EXTINF
    assert "tvg-logo" not in lines[1]


def test_render_xml_escapes_group_title():
    text = render_m3u(
        entries=[entry("a", "x.mp4")],
        entry_ids=["a"],
        group_title='A & "B" <C>',
        logo_lookup=lambda p: None,
        tpl="#EXTINF:-1 group-title=\"<group>\",<title>\n<base>/p?id=<eid>",
        base_url="http://x", source_id=1, token="T",
    )
    # the rendered EXTINF should escape
    assert "&amp;" in text
    assert "&quot;" in text
    assert "&lt;C&gt;" in text
