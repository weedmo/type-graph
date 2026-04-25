# tests/test_manifest.py
from pathlib import Path

from type_graph.manifest import Manifest, write_manifest, read_manifest, diff


def test_round_trip(tmp_path: Path) -> None:
    m = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2", 2.0)})
    p = tmp_path / "manifest.json"
    write_manifest(p, m)
    loaded = read_manifest(p)
    assert loaded == m


def test_diff_detects_change(tmp_path: Path) -> None:
    old = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2", 2.0)})
    new = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2X", 2.5), "c.py": ("h3", 3.0)})
    d = diff(old, new)
    assert set(d.changed) == {"b.py"}
    assert set(d.added) == {"c.py"}
    assert d.removed == []


def test_read_missing_returns_empty(tmp_path: Path) -> None:
    assert read_manifest(tmp_path / "nope.json").files == {}
