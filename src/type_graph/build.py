# src/type_graph/build.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import networkx as nx

from type_graph.cluster import Cluster
from type_graph.extract import ExtractedFunction
from type_graph.resolve import ResolveResult


@dataclass
class GraphPayload:
    version: str = "1"
    root: str = ""
    generated_at: str = ""
    stats: dict = field(default_factory=dict)
    clusters: list[dict] = field(default_factory=list)
    functions: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    unresolved_calls: list[dict] = field(default_factory=list)


def _function_to_dict(fn: ExtractedFunction, cluster_id: str) -> dict:
    return {
        "id": fn.id,
        "qualname": fn.qualname,
        "module": fn.module,
        "file": fn.file,
        "lineno": fn.lineno,
        "cluster_id": cluster_id,
        "signature": {
            "params": [{"name": p.name, "type": p.annotation} for p in fn.params],
            "returns": fn.returns,
        },
        "role": fn.docstring_first_line or "",
        "role_source": "docstring" if fn.docstring_first_line else "missing",
        "calls": [],
        "decorators": fn.decorators,
        "is_method": fn.is_method,
        "is_async": fn.is_async,
        "hash": f"sha1:{fn.body_hash}",
    }


def build_graph(
    *,
    functions: Iterable[ExtractedFunction],
    resolve: ResolveResult,
    clusters: list[Cluster],
    root: str,
) -> GraphPayload:
    source_functions = list(functions)
    function_ids = {fn.id for fn in source_functions}
    cluster_list = list(clusters)
    external_ids = sorted({e.dst for e in resolve.edges if e.dst not in function_ids})
    if external_ids:
        cluster_list.append(
            Cluster(
                id="__external__",
                label="external",
                path="__external__",
                function_ids=external_ids,
                child_clusters=[],
                summary="External or unmodeled call targets.",
            )
        )

    fn_to_cluster: dict[str, str] = {}
    for c in cluster_list:
        for fid in c.function_ids:
            fn_to_cluster[fid] = c.id

    fn_dicts = [_function_to_dict(fn, fn_to_cluster.get(fn.id, "")) for fn in source_functions]
    for eid in external_ids:
        module, _, qualname = eid.partition(":")
        fn_dicts.append(
            {
                "id": eid,
                "qualname": qualname or eid,
                "module": module,
                "file": "",
                "lineno": None,
                "cluster_id": "__external__",
                "signature": {"params": [], "returns": None},
                "role": "External or unmodeled call target.",
                "role_source": "external",
                "calls": [],
                "decorators": [],
                "is_method": False,
                "is_async": False,
                "hash": "",
            }
        )

    edge_dicts = [
        {
            "src": e.src,
            "dst": e.dst,
            "kind": "call",
            "passed_types": [],
            "lineno": e.lineno,
        }
        for e in resolve.edges
    ]

    unresolved = [
        {"src": u.src, "name": u.name, "lineno": u.lineno, "reason": u.reason}
        for u in resolve.unresolved
    ]

    g = nx.DiGraph()
    for f in fn_dicts:
        g.add_node(f["id"])
    for e in edge_dicts:
        g.add_edge(e["src"], e["dst"])

    cluster_dicts = [
        {
            "id": c.id,
            "label": c.label,
            "summary": c.summary,
            "path": c.path,
            "function_ids": list(c.function_ids),
            "child_clusters": list(c.child_clusters),
        }
        for c in cluster_list
    ]

    return GraphPayload(
        root=root,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        stats={
            "functions": g.number_of_nodes(),
            "edges": g.number_of_edges(),
            "clusters": len(cluster_dicts),
            "files": len({f["file"] for f in fn_dicts}),
        },
        clusters=cluster_dicts,
        functions=fn_dicts,
        edges=edge_dicts,
        unresolved_calls=unresolved,
    )


def write_graph_json(path: Path, payload: GraphPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.__dict__, indent=2, sort_keys=False))
