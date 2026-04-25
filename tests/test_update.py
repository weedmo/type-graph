# tests/test_update.py
import json
import shutil
from pathlib import Path

from type_graph.update import run_update


FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_update_short_circuits_when_unchanged(tmp_path: Path) -> None:
    out = tmp_path / "out"
    rc1 = run_update(
        root=FIXTURE, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=False,
    )
    assert rc1 == 0
    first_html_mtime = (out / "graph.html").stat().st_mtime

    rc2 = run_update(
        root=FIXTURE, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=False,
    )
    assert rc2 == 0
    assert (out / "graph.html").stat().st_mtime == first_html_mtime


class NoFunctionLLM:
    def summarize_function(self, name: str, body_excerpt: str) -> str:
        raise AssertionError(f"unexpected function LLM call for {name}")

    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str:
        return f"Cluster {cluster_id}"


def test_update_reuses_cached_roles_for_unchanged_bodies(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE, repo)
    out = tmp_path / "out"
    assert run_update(
        root=repo, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    ) == 0

    graph_path = out / "graph.json"
    payload = json.loads(graph_path.read_text())
    for f in payload["functions"]:
        f["role"] = f"Cached role for {f['id']}"
        f["role_source"] = "llm"
    graph_path.write_text(json.dumps(payload, indent=2))

    (repo / "api.py").write_text((repo / "api.py").read_text() + "\n# unchanged function bodies\n")

    assert run_update(
        root=repo, out_dir=out, llm_client=NoFunctionLLM(), infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    ) == 0
    updated = json.loads(graph_path.read_text())
    cached = [f for f in updated["functions"] if f["role_source"] == "llm"]
    assert cached
    assert all(f["role"].startswith("Cached role for ") for f in cached)
