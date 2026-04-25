# src/type_graph/update.py
from __future__ import annotations

import json
import sys
from pathlib import Path

from type_graph.discover import discover
from type_graph.manifest import diff, read_manifest, Manifest
from type_graph.pipeline import run


def run_update(
    *,
    root: Path,
    out_dir: Path,
    llm_client,
    infer: bool,
    cluster_depth: int,
    include_tests: bool,
    excludes,
    no_html: bool,
) -> int:
    root = root.resolve()
    new_files = discover(root, include_tests=include_tests, excludes=list(excludes))
    new_manifest = Manifest(files={f.relpath.as_posix(): (f.sha1, f.mtime) for f in new_files})
    old_manifest = read_manifest(out_dir / "manifest.json")
    d = diff(old_manifest, new_manifest)

    if not (d.added or d.changed or d.removed):
        print("type-graph: no changes since last run", file=sys.stderr)
        return 0

    cached_roles: dict[str, tuple[str, str, str]] = {}
    prev_path = out_dir / "graph.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text())
        for f in prev.get("functions", []):
            cached_roles[f["id"]] = (f.get("hash", ""), f.get("role", ""), f.get("role_source", "missing"))

    return run(
        root=root, out_dir=out_dir,
        llm_client=llm_client,
        infer=infer, cluster_depth=cluster_depth,
        include_tests=include_tests, excludes=excludes, no_html=no_html,
        cached_roles=cached_roles,
    )
