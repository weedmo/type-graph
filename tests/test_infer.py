# tests/test_infer.py
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import patch

from type_graph.build import GraphPayload
from type_graph.infer import _run_pyright, enhance_with_pyright


PYRIGHT_OUTPUT = {
    "generalDiagnostics": [{"severity": "error", "message": "bad type"}],
    "summary": {
        "errorCount": 1,
        "warningCount": 2,
        "informationCount": 3,
        "timeInSec": 0.25,
    },
}


def test_enhance_records_pyright_summary(tmp_path) -> None:
    payload = GraphPayload(
        root="/abs",
        stats={"functions": 1, "edges": 0, "clusters": 0, "files": 1},
        functions=[
            {
                "id": "m:foo",
                "qualname": "foo",
                "file": "/abs/m.py",
                "lineno": 12,
                "signature": {"params": [{"name": "x", "type": None}], "returns": None},
            }
        ],
    )
    with patch("type_graph.infer._run_pyright", return_value=PYRIGHT_OUTPUT):
        enhance_with_pyright(tmp_path, payload)
    assert payload.stats["pyright_errors"] == 1
    assert payload.stats["pyright_warnings"] == 2
    assert payload.stats["pyright_information"] == 3
    assert payload.stats["pyright_diagnostics"] == 1
    assert payload.functions[0]["signature"]["returns"] is None


def test_enhance_missing_pyright_raises() -> None:
    with patch("type_graph.infer._which_pyright", return_value=None):
        try:
            enhance_with_pyright("/tmp/x", GraphPayload())
        except SystemExit as e:
            assert e.code == 3
        else:
            raise AssertionError("expected SystemExit(3)")


def test_run_pyright_uses_timeout(tmp_path) -> None:
    cp = SimpleNamespace(stdout='{"summary": {}, "generalDiagnostics": []}', stderr="")
    with patch("type_graph.infer.subprocess.run", return_value=cp) as run:
        assert _run_pyright(tmp_path) == {"summary": {}, "generalDiagnostics": []}

    run.assert_called_once_with(
        ["pyright", "--outputjson", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_enhance_root_annotation_is_path() -> None:
    assert get_type_hints(enhance_with_pyright)["root"] is Path
