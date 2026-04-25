# src/type_graph/render.py
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from type_graph.build import GraphPayload


def write_html(path: Path, payload: GraphPayload) -> None:
    tmpl = resources.files("type_graph.templates").joinpath("graph.html.tmpl").read_text()
    embedded = json.dumps(payload.__dict__, indent=2).replace("</", "<\\/")
    html = tmpl.replace("__GRAPH_JSON__", embedded)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
