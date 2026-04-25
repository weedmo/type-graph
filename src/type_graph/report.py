# src/type_graph/report.py
from __future__ import annotations

from collections import Counter
from pathlib import Path

from type_graph.build import GraphPayload


def write_report(path: Path, payload: GraphPayload) -> None:
    s = payload.stats
    resolved = len(payload.edges)
    total_calls = resolved + len(payload.unresolved_calls)
    role_dist = Counter(f.get("role_source", "missing") for f in payload.functions)
    typed = sum(
        1
        for f in payload.functions
        if f["signature"]["returns"]
        and all(p["type"] for p in f["signature"]["params"])
    )

    lines = [
        "# type-graph Report",
        "",
        f"_Generated: {payload.generated_at}_",
        f"_Root: {payload.root}_",
        "",
        "## Summary",
        "",
        f"- Files: {s['files']}",
        f"- Functions: {s['functions']}",
        f"- Edges: {s['edges']}",
        f"- Clusters: {s['clusters']}",
        "",
        "## Honesty",
        "",
        f"- resolved calls / total calls: {resolved} / {total_calls}",
        f"- role_source: " + ", ".join(f"{k}={v}" for k, v in sorted(role_dist.items())),
        f"- fully-typed signatures / total: {typed} / {s['functions']}",
        "",
        "## Clusters",
        "",
    ]

    by_cluster: dict[str, list[dict]] = {}
    for f in payload.functions:
        by_cluster.setdefault(f.get("cluster_id", ""), []).append(f)

    for c in payload.clusters:
        lines.append(f"### {c['id']}")
        lines.append("")
        if c.get("summary"):
            lines.append(c["summary"])
            lines.append("")
        for f in by_cluster.get(c["id"], []):
            sig = f["signature"]
            params = ", ".join(
                f"{p['name']}: {p['type'] or 'Any'}" for p in sig["params"]
            )
            ret = sig["returns"] or "Any"
            role = f.get("role") or "(no description)"
            lines.append(f"- `{f['qualname']}({params}) -> {ret}` — {role}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
