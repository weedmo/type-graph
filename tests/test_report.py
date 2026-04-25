# tests/test_report.py
from pathlib import Path

from type_graph.build import GraphPayload
from type_graph.report import write_report


def test_report_contains_sections(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/abs/repo",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 3, "edges": 2, "clusters": 1, "files": 2},
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
