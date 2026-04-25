# src/type_graph/infer.py
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from type_graph.build import GraphPayload


def _which_pyright() -> str | None:
    return shutil.which("pyright")


def _run_pyright(root: Path) -> dict:
    cmd = ["pyright", "--outputjson", str(root)]
    # pyright exits non-zero when diagnostics found; JSON is still valid
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    try:
        return json.loads(cp.stdout or "{}")
    except json.JSONDecodeError:
        print(cp.stderr or "type-graph: pyright produced invalid JSON", file=sys.stderr)
        raise SystemExit(3)


def enhance_with_pyright(root: Path, payload: GraphPayload) -> None:
    if _which_pyright() is None:
        print("type-graph: --infer requested but pyright not found. pip install pyright.", file=sys.stderr)
        raise SystemExit(3)
    result = _run_pyright(Path(root))
    summary = result.get("summary", {})
    diagnostics = result.get("generalDiagnostics", [])
    payload.stats["pyright_errors"] = int(summary.get("errorCount", 0))
    payload.stats["pyright_warnings"] = int(summary.get("warningCount", 0))
    payload.stats["pyright_information"] = int(summary.get("informationCount", 0))
    payload.stats["pyright_diagnostics"] = len(diagnostics)
