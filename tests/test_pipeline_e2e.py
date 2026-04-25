# tests/test_pipeline_e2e.py
import json
from pathlib import Path

from type_graph import cli
from type_graph.pipeline import run


FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_pipeline_produces_four_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "out"
    rc = run(root=FIXTURE, out_dir=out, llm_client=None, infer=False, cluster_depth=3,
             include_tests=False, excludes=[], no_html=False)
    assert rc == 0

    payload_path = out / "graph.json"
    html_path = out / "graph.html"
    report_path = out / "REPORT.md"
    manifest_path = out / "manifest.json"

    assert payload_path.exists() and html_path.exists() and report_path.exists() and manifest_path.exists()
    payload = json.loads(payload_path.read_text())
    fn_ids = {f["id"] for f in payload["functions"]}
    assert "sample_repo.models:normalize_name" in fn_ids
    assert "sample_repo.api:make_user" in fn_ids
    edges = payload["edges"]
    assert any(e["src"] == "sample_repo.api:make_user" and e["dst"] == "sample_repo.models:normalize_name" for e in edges)


def test_cli_entrypoint_runs(tmp_path: Path) -> None:
    import subprocess, sys

    out = tmp_path / "out"
    cp = subprocess.run(
        [sys.executable, "-m", "type_graph", str(FIXTURE), "--out", str(out), "--no-llm"],
        capture_output=True, text=True,
    )
    assert cp.returncode == 0, cp.stderr
    assert (out / "graph.json").exists()


def test_cli_does_not_construct_llm_before_pipeline_needs_it(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TYPE_GRAPH_ANTHROPIC_MODEL", raising=False)
    out = tmp_path / "out"

    rc = cli.main([str(FIXTURE), "--out", str(out), "--exclude", "*.py"])

    assert rc == 0
    assert (out / "graph.json").exists()
