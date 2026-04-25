# tests/test_label.py
from type_graph.build import GraphPayload
from type_graph.label import label_payload


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def summarize_function(self, name: str, body_excerpt: str) -> str:
        self.calls.append(("fn", [name]))
        return f"Auto: {name}"

    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str:
        self.calls.append(("cluster", [cluster_id]))
        return f"Cluster summary for {cluster_id}"


def make_fn(id_, role, source):
    return {
        "id": id_,
        "qualname": id_.split(":", 1)[1],
        "role": role,
        "role_source": source,
        "signature": {"params": [], "returns": None},
        "cluster_id": "m",
        "file": "m.py",
        "lineno": 1,
        "hash": "sha1:abc",
    }


def test_fills_missing_roles_and_cluster_summary() -> None:
    payload = GraphPayload(
        root="/r",
        stats={"functions": 2, "edges": 0, "clusters": 1, "files": 1},
        clusters=[{"id": "m", "label": "m", "summary": "", "path": "m",
                   "function_ids": ["m:a", "m:b"], "child_clusters": []}],
        functions=[
            make_fn("m:a", "Do A.", "docstring"),
            make_fn("m:b", "", "missing"),
        ],
        edges=[],
        unresolved_calls=[],
    )
    client = FakeClient()
    label_payload(payload, client=client)
    by_id = {f["id"]: f for f in payload.functions}
    assert by_id["m:a"]["role_source"] == "docstring"
    assert by_id["m:b"]["role_source"] == "llm"
    assert by_id["m:b"]["role"] == "Auto: b"
    assert payload.clusters[0]["summary"] == "Cluster summary for m"


def test_skip_when_no_llm_flag() -> None:
    payload = GraphPayload(
        root="/r",
        stats={"functions": 1, "edges": 0, "clusters": 1, "files": 1},
        clusters=[{"id": "m", "label": "m", "summary": "", "path": "m",
                   "function_ids": ["m:b"], "child_clusters": []}],
        functions=[make_fn("m:b", "", "missing")],
        edges=[], unresolved_calls=[],
    )
    label_payload(payload, client=None)
    assert payload.functions[0]["role"] == ""
    assert payload.functions[0]["role_source"] == "missing"
    assert payload.clusters[0]["summary"] == ""


def test_cached_role_reused_without_function_llm_call() -> None:
    payload = GraphPayload(
        root="/r",
        stats={"functions": 1, "edges": 0, "clusters": 1, "files": 1},
        clusters=[{"id": "m", "label": "m", "summary": "", "path": "m",
                   "function_ids": ["m:b"], "child_clusters": []}],
        functions=[make_fn("m:b", "", "missing")],
        edges=[], unresolved_calls=[],
    )
    client = FakeClient()
    label_payload(payload, client=client, cached_roles={"m:b": ("sha1:abc", "Cached role.", "llm")})
    assert payload.functions[0]["role"] == "Cached role."
    assert payload.functions[0]["role_source"] == "llm"
    assert ("fn", ["b"]) not in client.calls
