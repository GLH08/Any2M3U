from any2m3u.m3u.filters import filter_entries, FileEntry


def entry(path: str) -> FileEntry:
    return {"path": path, "size": 1, "mtime": 0.0, "etag": None}


def test_no_filters_passes_all():
    entries = [entry("a.mp4"), entry("b.mkv"), entry("c.txt")]
    out = filter_entries(entries, include_exts=None, exclude_keywords=None, include_paths=None)
    assert out == entries


def test_include_exts():
    entries = [entry("a.mp4"), entry("b.mkv"), entry("c.txt")]
    out = filter_entries(entries, include_exts="mp4,mkv", exclude_keywords=None, include_paths=None)
    assert [e["path"] for e in out] == ["a.mp4", "b.mkv"]


def test_include_exts_case_insensitive():
    entries = [entry("A.MP4"), entry("b.Mp4")]
    out = filter_entries(entries, include_exts="mp4", exclude_keywords=None, include_paths=None)
    assert len(out) == 2


def test_exclude_keywords():
    entries = [entry("movie.mp4"), entry("sample.mp4"), entry("trailer.mkv")]
    out = filter_entries(entries, include_exts=None, exclude_keywords="sample,trailer", include_paths=None)
    assert [e["path"] for e in out] == ["movie.mp4"]


def test_include_paths_prefix():
    entries = [entry("Movies/a.mp4"), entry("Shows/b.mkv"), entry("Movies/c.mp4")]
    out = filter_entries(entries, include_exts=None, exclude_keywords=None, include_paths="Movies/")
    assert [e["path"] for e in out] == ["Movies/a.mp4", "Movies/c.mp4"]


def test_combined():
    entries = [entry("Movies/a.mp4"), entry("Movies/b.txt"), entry("Shows/c.mp4"), entry("Movies/sample.mp4")]
    out = filter_entries(
        entries, include_exts="mp4", exclude_keywords="sample", include_paths="Movies/"
    )
    assert [e["path"] for e in out] == ["Movies/a.mp4"]
