# src/type_graph/cluster.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


@dataclass
class Cluster:
    id: str
    label: str
    path: str
    function_ids: list[str] = field(default_factory=list)
    child_clusters: list[str] = field(default_factory=list)
    summary: str = ""


_ROOT_CLUSTER_ID = "__root__"


def _leaf_cluster_for(module: str, file_path: str, depth: int) -> str:
    """Derive cluster id from the dotted module name (which already includes any
    root_package prefix). For non-__init__ files, the function lives in its
    parent package (drop the last module segment). For __init__.py, functions
    belong to the package itself. Truncated to `depth` segments."""
    parts = [p for p in module.split(".") if p]
    is_init = Path(file_path).name == "__init__.py"
    leaf_parts = parts if is_init else parts[:-1]
    if not leaf_parts:
        return _ROOT_CLUSTER_ID
    return ".".join(leaf_parts[:depth])


def build_clusters(
    functions: Iterable[Mapping[str, str]],
    *,
    depth: int = 3,
) -> list[Cluster]:
    if depth is not None and depth < 1:
        raise ValueError("depth must be >= 1")

    clusters: dict[str, Cluster] = {}

    def ensure(path_dotted: str) -> Cluster:
        if path_dotted in clusters:
            return clusters[path_dotted]
        c = Cluster(
            id=path_dotted,
            label="(root)" if path_dotted == _ROOT_CLUSTER_ID else path_dotted.split(".")[-1],
            path="" if path_dotted == _ROOT_CLUSTER_ID else path_dotted.replace(".", "/"),
        )
        clusters[path_dotted] = c
        return c

    for f in functions:
        leaf_id = _leaf_cluster_for(f["module"], f["file"], depth)
        leaf = ensure(leaf_id)
        leaf.function_ids.append(f["id"])
        if leaf_id == _ROOT_CLUSTER_ID:
            continue
        parts = leaf_id.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            child = ".".join(parts[: i + 1])
            ensure(parent)
            ensure(child)
            if child not in clusters[parent].child_clusters:
                clusters[parent].child_clusters.append(child)

    return list(clusters.values())
