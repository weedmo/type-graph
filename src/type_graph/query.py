# src/type_graph/query.py
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx


def _load(graph_path: Path) -> dict:
    return json.loads(Path(graph_path).read_text())


def explain(function_id: str, *, graph_path: Path) -> int:
    payload = _load(graph_path)
    fn = next((f for f in payload["functions"] if f["id"] == function_id), None)
    if fn is None:
        print(f"type-graph: function not found: {function_id}", file=sys.stderr)
        return 2
    sig = fn["signature"]
    params = ", ".join(f"{p['name']}: {p['type'] or 'Any'}" for p in sig["params"])
    print(f"{fn['qualname']}({params}) -> {sig['returns'] or 'Any'}")
    print(f"  role [{fn.get('role_source','?')}]: {fn.get('role','') or '(none)'}")
    print(f"  file: {fn.get('file','?')}:{fn.get('lineno','?')}")
    callers = [e["src"] for e in payload["edges"] if e["dst"] == function_id]
    callees = [e["dst"] for e in payload["edges"] if e["src"] == function_id]
    print("  Callers: " + (", ".join(callers) if callers else "(none)"))
    print("  Callees: " + (", ".join(callees) if callees else "(none)"))
    return 0


def shortest_call_path(a: str, b: str, *, graph_path: Path) -> list[str] | None:
    payload = _load(graph_path)
    # Rebuilding the graph per call keeps the v0 query path simple.
    g = nx.DiGraph()
    for f in payload["functions"]:
        g.add_node(f["id"])
    for e in payload["edges"]:
        g.add_edge(e["src"], e["dst"])
    try:
        return nx.shortest_path(g, a, b)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def query(question: str, *, graph_path: Path, client) -> int:
    if client is None:
        print("type-graph: query requires an LLM client; remove --no-llm", file=sys.stderr)
        return 3
    payload = _load(graph_path)
    cluster_lines = [f"- {c['id']}: {c.get('summary','')}" for c in payload["clusters"]]
    function_names = [f["id"].replace(":", ".") for f in payload["functions"][:200]]
    context_str = (
        "Clusters:\n" + "\n".join(cluster_lines)
        + "\n\nA few function names:\n" + ", ".join(function_names)
    )
    try:
        ans = client.answer_question(question, context_str)
        print(ans)
        return 0
    except Exception as exc:
        print(f"type-graph: query failed: {exc}", file=sys.stderr)
        return 2
