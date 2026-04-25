# src/type_graph/render.py
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from type_graph.build import GraphPayload


def write_html(path: Path, payload: GraphPayload) -> None:
    # v0 threat model: this report is for analyzing your own codebase, so the
    # embedded payload is trusted input. Full sanitization for user-supplied code
    # is out of scope; closing script tags are escaped below, but script openers
    # are not.
    tmpl = resources.files("type_graph.templates").joinpath("graph.html.tmpl").read_text()
    # Prevent JSON string values from prematurely closing the surrounding
    # <script>. HTML comment markers (<!-- and -->) are low-risk for v0 and are
    # intentionally not escaped.
    embedded = json.dumps(payload.__dict__, indent=2).replace("</", "<\\/")
    html = tmpl.replace("__GRAPH_JSON__", embedded)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
