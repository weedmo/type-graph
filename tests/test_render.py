# tests/test_render.py
import json
from pathlib import Path

from type_graph.build import GraphPayload
from type_graph.render import write_html


def test_html_embeds_payload(tmp_path: Path) -> None:
    payload = GraphPayload(
        root="/r",
        generated_at="2026-04-26T00:00:00Z",
        stats={"functions": 0, "edges": 0, "clusters": 0, "files": 0},
        clusters=[],
        functions=[],
        edges=[],
        unresolved_calls=[],
    )
    out = tmp_path / "graph.html"
    write_html(out, payload)
    text = out.read_text()
    assert "<!doctype html>" in text
    assert "__GRAPH_JSON__" not in text
    assert "cytoscape.use(cytoscapeDagre)" in text
    embedded_marker = '"version": "1"'
    assert embedded_marker in text
    start = text.index("const GRAPH = ") + len("const GRAPH = ")
    end = text.index(";\n", start)
    parsed = json.loads(text[start:end])
    assert parsed["root"] == "/r"
