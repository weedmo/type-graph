# tests/test_cluster.py
from type_graph.cluster import build_clusters, Cluster


def make_fn(id_: str, module: str, file: str) -> dict:
    return {"id": id_, "module": module, "file": file}


def test_simple_package_cluster() -> None:
    fns = [
        make_fn("pkg.a:f", "pkg.a", "pkg/a.py"),
        make_fn("pkg.b:g", "pkg.b", "pkg/b.py"),
    ]
    clusters = build_clusters(fns, depth=3)
    by_id = {c.id: c for c in clusters}
    assert "pkg" in by_id
    assert set(by_id["pkg"].function_ids) == {"pkg.a:f", "pkg.b:g"}


def test_nested_clusters_have_parent_child() -> None:
    fns = [
        make_fn("pkg.sub.a:f", "pkg.sub.a", "pkg/sub/a.py"),
    ]
    clusters = build_clusters(fns, depth=3)
    by_id = {c.id: c for c in clusters}
    assert "pkg" in by_id and "pkg.sub" in by_id
    assert "pkg.sub" in by_id["pkg"].child_clusters


def test_depth_limit_flattens_deep_modules() -> None:
    fns = [
        make_fn("a.b.c.d:f", "a.b.c.d", "a/b/c/d.py"),
    ]
    clusters = build_clusters(fns, depth=2)
    cluster_ids = {c.id for c in clusters}
    assert "a.b" in cluster_ids
    assert "a.b.c" not in cluster_ids
    assert "a.b.c.d" not in cluster_ids
    placed = [c for c in clusters if "a.b.c.d:f" in c.function_ids]
    assert len(placed) == 1 and placed[0].id == "a.b"


def test_init_belongs_to_package_cluster() -> None:
    fns = [make_fn("pkg:init", "pkg", "pkg/__init__.py")]
    clusters = build_clusters(fns, depth=3)
    by_id = {c.id: c for c in clusters}
    assert by_id["pkg"].function_ids == ["pkg:init"]


def test_top_level_module_with_root_package_prefix() -> None:
    fns = [
        make_fn("sample_repo.models:f", "sample_repo.models", "models.py"),
        make_fn("sample_repo.api:g", "sample_repo.api", "api.py"),
        make_fn("sample_repo:init", "sample_repo", "__init__.py"),
    ]
    clusters = build_clusters(fns, depth=3)
    by_id = {c.id: c for c in clusters}
    assert "sample_repo" in by_id
    assert set(by_id["sample_repo"].function_ids) >= {
        "sample_repo:init",
        "sample_repo.models:f",
        "sample_repo.api:g",
    }
    assert "__root__" not in by_id
