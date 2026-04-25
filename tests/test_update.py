# tests/test_update.py
import json
import shutil
from pathlib import Path
from typing import Callable, get_type_hints

from type_graph.llm import LLMClient
from type_graph.update import run_update


FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_run_update_annotations_are_specific() -> None:
    hints = get_type_hints(run_update)

    assert hints["llm_client"] == LLMClient | Callable[[], LLMClient] | None
    assert hints["excludes"] == list[str]


def test_update_first_run_without_manifest_runs_pipeline(tmp_path: Path) -> None:
    out = tmp_path / "out"

    assert not (out / "manifest.json").exists()
    rc = run_update(
        root=FIXTURE, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    )

    assert rc == 0
    assert (out / "manifest.json").exists()
    assert (out / "graph.json").exists()


def test_update_short_circuits_when_unchanged(tmp_path: Path, capsys) -> None:
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
    captured = capsys.readouterr()
    assert captured.err == "type-graph: no changes since last run\n"
    assert (out / "graph.html").stat().st_mtime == first_html_mtime


class NoFunctionLLM:
    def summarize_function(self, name: str, body_excerpt: str) -> str:
        raise AssertionError(f"unexpected function LLM call for {name}")

    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str:
        return f"Cluster {cluster_id}"


class StaticLLM:
    def summarize_function(self, name: str, body_excerpt: str) -> str:
        return f"Role for {name}"

    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str:
        return f"Cluster {cluster_id}"


def test_update_accepts_llm_client_factory(tmp_path: Path) -> None:
    out = tmp_path / "out"
    factory_calls = 0

    def build_client() -> LLMClient:
        nonlocal factory_calls
        factory_calls += 1
        return StaticLLM()

    assert run_update(
        root=FIXTURE, out_dir=out, llm_client=build_client, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    ) == 0

    graph = json.loads((out / "graph.json").read_text())
    greet = next(f for f in graph["functions"] if f["id"] == "sample_repo.api:greet")
    assert factory_calls == 1
    assert greet["role_source"] == "llm"
    assert greet["role"] == "Role for greet"


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


def test_update_removed_file_triggers_rerun_and_rewrites_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE, repo)
    out = tmp_path / "out"
    assert run_update(
        root=repo, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    ) == 0

    (repo / "api.py").unlink()

    assert run_update(
        root=repo, out_dir=out, llm_client=None, infer=False,
        cluster_depth=3, include_tests=False, excludes=[], no_html=True,
    ) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert "api.py" not in manifest["files"]
    assert "models.py" in manifest["files"]
    graph = json.loads((out / "graph.json").read_text())
    assert all(f.get("file") != "api.py" for f in graph["functions"])
