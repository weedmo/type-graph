# tests/test_discover.py
import hashlib
from pathlib import Path
import textwrap
from type_graph.discover import discover, DiscoveredFile


def write(p: Path, body: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))


def test_discover_walks_python_files(tmp_path: Path) -> None:
    write(tmp_path / "a.py", "x = 1\n")
    write(tmp_path / "pkg/b.py", "y = 2\n")
    write(tmp_path / "pkg/__init__.py")
    write(tmp_path / "README.md", "# unrelated")
    write(tmp_path / "__pycache__/c.py", "")
    write(tmp_path / "tests/test_x.py", "")

    found = discover(tmp_path, include_tests=False)

    rels = sorted(f.relpath.as_posix() for f in found)
    assert rels == ["a.py", "pkg/__init__.py", "pkg/b.py"]
    assert all(isinstance(f, DiscoveredFile) for f in found)
    assert all(f.sha1 and f.mtime > 0 for f in found)


def test_discover_includes_tests_when_requested(tmp_path: Path) -> None:
    write(tmp_path / "tests/test_x.py", "x = 1\n")
    found = discover(tmp_path, include_tests=True)
    assert any(f.relpath.as_posix() == "tests/test_x.py" for f in found)


def test_discover_respects_exclude_globs(tmp_path: Path) -> None:
    write(tmp_path / "a.py", "")
    write(tmp_path / "migrations/0001.py", "")
    found = discover(tmp_path, include_tests=False, excludes=["**/migrations/**"])
    rels = [f.relpath.as_posix() for f in found]
    assert "a.py" in rels
    assert all("migrations" not in r for r in rels)


def test_discover_stats_before_reading_so_sha1_matches_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "a.py"
    old_contents = b"x = 1\n"
    discovered_contents = b"x = 2\n"
    target.write_bytes(old_contents)
    root = tmp_path.resolve()
    original_rglob = Path.rglob
    original_stat = Path.stat
    original_read_bytes = Path.read_bytes
    events: list[str] = []

    def rglob_one_file(self: Path, pattern: str):
        if self == root and pattern == "*.py":
            return [target]
        return original_rglob(self, pattern)

    def stat_and_update_file(self: Path, *args, **kwargs):
        if self == target:
            events.append("stat")
            target.write_bytes(discovered_contents)
        return original_stat(self, *args, **kwargs)

    def read_bytes_and_record(self: Path):
        if self == target:
            events.append("read")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "rglob", rglob_one_file)
    monkeypatch.setattr(Path, "stat", stat_and_update_file)
    monkeypatch.setattr(Path, "read_bytes", read_bytes_and_record)

    found = discover(root, include_tests=True)

    assert events == ["stat", "read"]
    assert found[0].sha1 == hashlib.sha1(
        discovered_contents, usedforsecurity=False
    ).hexdigest()
