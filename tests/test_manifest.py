# tests/test_manifest.py
import json
from pathlib import Path

from type_graph.manifest import Manifest, write_manifest, read_manifest, diff


def test_round_trip(tmp_path: Path) -> None:
    m = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2", 2.0)})
    p = tmp_path / "manifest.json"
    write_manifest(p, m)
    loaded = read_manifest(p)
    assert loaded == m


def test_write_manifest_preserves_existing_file_if_write_fails(
    tmp_path: Path, monkeypatch
) -> None:
    original = Manifest(files={"a.py": ("h1", 1.0)})
    replacement = Manifest(files={"a.py": ("h2", 2.0)})
    p = tmp_path / "manifest.json"
    write_manifest(p, original)
    original_text = p.read_text()

    original_write_text = Path.write_text

    def fail_write_text(self: Path, data: str, *args, **kwargs) -> int:
        original_write_text(self, "partial", *args, **kwargs)
        raise RuntimeError("write failed")

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    try:
        write_manifest(p, replacement)
    except RuntimeError:
        pass

    assert p.read_text() == original_text


def test_manifest_payload_has_ignored_schema_version(tmp_path: Path) -> None:
    m = Manifest(files={"a.py": ("h1", 1.0)})
    p = tmp_path / "manifest.json"
    write_manifest(p, m)

    raw = json.loads(p.read_text())
    assert raw["schema_version"] == 1

    raw["schema_version"] = 999
    p.write_text(json.dumps(raw))

    assert read_manifest(p) == m


def test_diff_detects_change(tmp_path: Path) -> None:
    old = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2", 2.0)})
    new = Manifest(files={"a.py": ("h1", 1.0), "b.py": ("h2X", 2.5), "c.py": ("h3", 3.0)})
    d = diff(old, new)
    assert set(d.changed) == {"b.py"}
    assert set(d.added) == {"c.py"}
    assert d.removed == []


def test_read_missing_returns_empty(tmp_path: Path) -> None:
    assert read_manifest(tmp_path / "nope.json").files == {}
