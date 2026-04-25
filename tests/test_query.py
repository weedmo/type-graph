# tests/test_query.py
import json
from pathlib import Path

from type_graph.cli import main
from type_graph.pipeline import run
from type_graph.query import explain, shortest_call_path


FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def _ensure_graph(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    run(root=FIXTURE, out_dir=out, llm_client=None, infer=False, cluster_depth=3,
        include_tests=False, excludes=[], no_html=True)
    return out / "graph.json"


def test_explain_prints_signature_and_callers(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    explain("sample_repo.models:normalize_name", graph_path=graph)
    out = capsys.readouterr().out
    assert "normalize_name" in out
    assert "Callers:" in out and "sample_repo.api:make_user" in out


def test_shortest_call_path(tmp_path: Path) -> None:
    graph = _ensure_graph(tmp_path)
    chain = shortest_call_path(
        "sample_repo.api:make_user",
        "sample_repo.models:normalize_name",
        graph_path=graph,
    )
    assert chain == ["sample_repo.api:make_user", "sample_repo.models:normalize_name"]


def test_cli_path_subcommand_prints_chain(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    rc = main(["path", "sample_repo.api:make_user", "sample_repo.models:normalize_name", str(graph)])
    assert rc == 0
    assert "sample_repo.api:make_user -> sample_repo.models:normalize_name" in capsys.readouterr().out


def test_cli_query_no_llm_returns_3(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    rc = main(["query", "what calls normalize_name?", str(graph), "--no-llm"])
    assert rc == 3
    assert "requires an LLM client" in capsys.readouterr().err
