# src/type_graph/discover.py
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pathspec


@dataclass(frozen=True)
class DiscoveredFile:
    relpath: Path
    abspath: Path
    mtime: float
    sha1: str


_DEFAULT_EXCLUDES = [
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.git/**",
    "**/build/**",
    "**/dist/**",
    "**/*.egg-info/**",
]


def discover(
    root: Path,
    *,
    include_tests: bool = False,
    excludes: Iterable[str] | None = None,
) -> list[DiscoveredFile]:
    root = root.resolve()
    patterns = list(_DEFAULT_EXCLUDES)
    if not include_tests:
        patterns.append("**/tests/**")
        patterns.append("**/test_*.py")
    if excludes:
        patterns.extend(excludes)
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    out: list[DiscoveredFile] = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if spec.match_file(rel.as_posix()):
            continue
        st = p.stat()
        data = p.read_bytes()
        out.append(
            DiscoveredFile(
                relpath=rel,
                abspath=p,
                mtime=st.st_mtime,
                sha1=hashlib.sha1(data, usedforsecurity=False).hexdigest(),
            )
        )
    return out
