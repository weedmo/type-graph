# src/type_graph/manifest.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Manifest:
    files: dict[str, tuple[str, float]] = field(default_factory=dict)


@dataclass
class Diff:
    added: list[str]
    changed: list[str]
    removed: list[str]


def write_manifest(path: Path, m: Manifest) -> None:
    payload = {"files": {k: list(v) for k, v in m.files.items()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def read_manifest(path: Path) -> Manifest:
    if not path.exists():
        return Manifest()
    raw = json.loads(path.read_text())
    return Manifest(files={k: (v[0], float(v[1])) for k, v in raw.get("files", {}).items()})


def diff(old: Manifest, new: Manifest) -> Diff:
    added: list[str] = []
    changed: list[str] = []
    removed: list[str] = []
    for k, v in new.files.items():
        if k not in old.files:
            added.append(k)
        elif old.files[k][0] != v[0]:
            changed.append(k)
    for k in old.files:
        if k not in new.files:
            removed.append(k)
    return Diff(added=added, changed=changed, removed=removed)
