# src/type_graph/pipeline.py
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable, Iterable, Mapping

from type_graph.build import GraphPayload, build_graph, write_graph_json
from type_graph.cluster import build_clusters
from type_graph.discover import discover
from type_graph.extract import extract_functions
from type_graph.label import label_payload
from type_graph.llm import LLMClient
from type_graph.manifest import Manifest, write_manifest
from type_graph.modules import path_to_module
from type_graph.render import write_html
from type_graph.report import write_report
from type_graph.resolve import build_import_map, resolve_calls
from type_graph.types_norm import normalize_annotation


def _normalize_function(fn) -> None:
    fn.params = [
        dataclasses.replace(p, annotation=normalize_annotation(p.annotation))
        for p in fn.params
    ]
    fn.returns = normalize_annotation(fn.returns)


def _cached_role_is_reusable(
    fn: dict,
    cached_roles: Mapping[str, tuple[str, str, str]] | None,
) -> bool:
    if not cached_roles:
        return False
    cached = cached_roles.get(fn["id"])
    return bool(
        cached
        and cached[0] == fn.get("hash")
        and cached[1]
        and cached[2] not in {"missing", "failed"}
    )


def _payload_needs_llm(
    payload: GraphPayload,
    cached_roles: Mapping[str, tuple[str, str, str]] | None,
) -> bool:
    for f in payload.functions:
        if f.get("role_source") == "missing" and not _cached_role_is_reusable(f, cached_roles):
            return True

    by_id = {f["id"] for f in payload.functions}
    return any(
        any(fid in by_id for fid in c.get("function_ids", []))
        for c in payload.clusters
    )


def run(
    *,
    root: Path,
    out_dir: Path,
    llm_client: LLMClient | None,
    infer: bool,
    cluster_depth: int,
    include_tests: bool,
    excludes: Iterable[str],
    no_html: bool,
    cached_roles: Mapping[str, tuple[str, str, str]] | None = None,
    llm_client_factory: Callable[[], LLMClient] | None = None,
) -> int:
    root = root.resolve()
    files = discover(root, include_tests=include_tests, excludes=list(excludes))
    root_package = root.name if (root / "__init__.py").exists() else None

    all_functions = []
    fn_relpaths: dict[str, str] = {}
    imports_by_module: dict[str, dict[str, str]] = {}
    for f in files:
        module = path_to_module(f.relpath, root_package=root_package)
        funcs = extract_functions(f.abspath, module=module)
        for fn in funcs:
            _normalize_function(fn)
            fn_relpaths[fn.id] = f.relpath.as_posix()
        all_functions.extend(funcs)
        imports_by_module[module] = build_import_map(f.abspath)

    fn_index = {fn.id: fn for fn in all_functions}
    res = resolve_calls(all_functions, fn_index=fn_index, imports_by_module=imports_by_module)

    cluster_seed = [{"id": fn.id, "module": fn.module, "file": fn_relpaths[fn.id]} for fn in all_functions]
    clusters = build_clusters(cluster_seed, depth=cluster_depth)

    payload = build_graph(
        functions=all_functions,
        resolve=res,
        clusters=clusters,
        root=str(root),
    )

    if infer:
        from type_graph.infer import enhance_with_pyright
        enhance_with_pyright(root, payload)

    label_client = llm_client
    if (
        label_client is None
        and llm_client_factory is not None
        and _payload_needs_llm(payload, cached_roles)
    ):
        label_client = llm_client_factory()
    label_payload(payload, client=label_client, cached_roles=cached_roles)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_graph_json(out_dir / "graph.json", payload)
    write_report(out_dir / "REPORT.md", payload)
    if not no_html:
        write_html(out_dir / "graph.html", payload)

    manifest = Manifest(files={f.relpath.as_posix(): (f.sha1, f.mtime) for f in files})
    write_manifest(out_dir / "manifest.json", manifest)

    return 0
