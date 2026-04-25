# tests/test_build.py
import json
from pathlib import Path

from type_graph.build import build_graph, write_graph_json
from type_graph.cluster import Cluster
from type_graph.extract import ExtractedFunction, Param, CallSite
from type_graph.resolve import ResolveResult, ResolvedEdge, UnresolvedCall


def make_fn(id_: str, module: str) -> ExtractedFunction:
    return ExtractedFunction(
        id=id_,
        qualname=id_.split(":", 1)[1],
        module=module,
        file=f"{module.replace('.', '/')}.py",
        lineno=1,
        params=[Param("x", "int")],
        returns="int",
        docstring_first_line=None,
        decorators=[],
        is_method=False,
        is_async=False,
        call_sites=[CallSite(name="g", lineno=2)],
        body_hash="abc",
    )


def test_builds_graph_json(tmp_path: Path) -> None:
    f1 = make_fn("m:f", "m")
    f2 = make_fn("m:g", "m")
    res = ResolveResult(
        edges=[ResolvedEdge("m:f", "m:g", lineno=2)],
        unresolved=[UnresolvedCall("m:f", "?", 9, "unknown-name")],
    )
    clusters = [Cluster(id="m", label="m", path="m", function_ids=["m:f", "m:g"])]
    g = build_graph(
        functions=[f1, f2],
        resolve=res,
        clusters=clusters,
        root="/abs/path",
    )
    out = tmp_path / "graph.json"
    write_graph_json(out, g)
    payload = json.loads(out.read_text())

    assert payload["version"] == "1"
    assert payload["root"] == "/abs/path"
    assert payload["stats"]["functions"] == 2
    assert payload["stats"]["edges"] == 1
    assert payload["stats"]["clusters"] == 1
    assert {f["id"] for f in payload["functions"]} == {"m:f", "m:g"}
    assert payload["edges"][0] == {
        "src": "m:f",
        "dst": "m:g",
        "kind": "call",
        "passed_types": [],
        "lineno": 2,
    }
    assert payload["unresolved_calls"][0]["reason"] == "unknown-name"


def test_adds_external_cluster_for_unmodeled_resolved_dst(tmp_path: Path) -> None:
    f1 = make_fn("m:f", "m")
    res = ResolveResult(
        edges=[ResolvedEdge("m:f", "numpy:array", lineno=4)],
        unresolved=[],
    )
    clusters = [Cluster(id="m", label="m", path="m", function_ids=["m:f"])]
    g = build_graph(functions=[f1], resolve=res, clusters=clusters, root="/abs/path")
    out = tmp_path / "graph.json"
    write_graph_json(out, g)
    payload = json.loads(out.read_text())

    assert any(c["id"] == "__external__" for c in payload["clusters"])
    external = next(f for f in payload["functions"] if f["id"] == "numpy:array")
    assert external["cluster_id"] == "__external__"
    assert external["role_source"] == "external"
