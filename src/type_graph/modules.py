# src/type_graph/modules.py
from __future__ import annotations

from pathlib import Path


def path_to_module(relpath: Path, *, root_package: str | None = None) -> str:
    parts = list(relpath.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if root_package:
        parts.insert(0, root_package)
    return ".".join(parts)
