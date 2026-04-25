# tests/test_report.py
from pathlib import Path

from type_graph.build import GraphPayload
from type_graph.report import write_report


def test_report_contains_sections(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/abs/repo",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 3, "edges": 1, "clusters": 1, "files": 2},
        clusters=[
            {
                "id": "m",
                "label": "m",
                "summary": "Module m.",
                "path": "m",
                "function_ids": ["m:a", "m:b", "m:c"],
                "child_clusters": [],
            }
        ],
        functions=[
            {"id": "m:a", "qualname": "a", "role": "Do A.", "role_source": "docstring",
             "signature": {"params": [{"name": "x", "type": "int"}], "returns": "int"}},
            {"id": "m:b", "qualname": "b", "role": "", "role_source": "missing",
             "signature": {"params": [{"name": "x", "type": None}], "returns": None}},
            {"id": "m:c", "qualname": "c", "role": "Do C.", "role_source": "llm",
             "signature": {"params": [], "returns": "None"}},
        ],
        edges=[{"src": "m:a", "dst": "m:b", "kind": "call", "passed_types": [], "lineno": 1}],
        unresolved_calls=[{"src": "m:a", "name": "x.y", "lineno": 5, "reason": "dynamic-attr"}],
    )
    out = tmp_path / "REPORT.md"
    write_report(out, payload)
    text = out.read_text()
    assert "# type-graph Report" in text
    assert "## Summary" in text
    assert "## Honesty" in text
    assert "## Clusters" in text
    assert "resolved calls / total calls: 1 / 2" in text
    assert "role_source: docstring=1, llm=1, missing=1" in text


def test_report_escapes_backticks_in_qualnames(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/abs/repo",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 1, "edges": 0, "clusters": 1, "files": 1},
        clusters=[
            {
                "id": "m",
                "label": "m",
                "summary": "",
                "path": "m",
                "function_ids": ["m:bad"],
                "child_clusters": [],
            }
        ],
        functions=[
            {
                "id": "m:bad",
                "qualname": "bad`name",
                "cluster_id": "m",
                "role": "Do bad.",
                "role_source": "docstring",
                "signature": {"params": [], "returns": None},
            }
        ],
        edges=[],
        unresolved_calls=[],
    )
    out = tmp_path / "REPORT.md"
    write_report(out, payload)
    text = out.read_text()
    assert "`bad'name() -> Any`" in text
    assert "`bad`name() -> Any`" not in text


def test_report_handles_empty_payload(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/abs/repo",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 0, "edges": 0, "clusters": 0, "files": 0},
        clusters=[],
        functions=[],
        edges=[],
        unresolved_calls=[],
    )
    out = tmp_path / "REPORT.md"
    write_report(out, payload)
    text = out.read_text()
    assert "role_source: (none)" in text
    assert "resolved calls / total calls: 0 / 0" in text


def test_report_counts_resolved_call_sites_not_unique_edges(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/abs/repo",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 2, "edges": 1, "clusters": 1, "files": 1},
        clusters=[],
        functions=[],
        edges=[
            {"src": "m:a", "dst": "m:b", "kind": "call", "passed_types": [], "lineno": 1},
            {"src": "m:a", "dst": "m:b", "kind": "call", "passed_types": [], "lineno": 2},
        ],
        unresolved_calls=[{"src": "m:a", "name": "x.y", "lineno": 5, "reason": "dynamic-attr"}],
    )
    out = tmp_path / "REPORT.md"
    write_report(out, payload)
    text = out.read_text()
    assert "resolved calls / total calls: 2 / 3" in text
