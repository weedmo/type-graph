# src/type_graph/resolve.py
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from type_graph.extract import ExtractedFunction


@dataclass(frozen=True)
class ResolvedEdge:
    src: str
    dst: str
    lineno: int


@dataclass(frozen=True)
class UnresolvedCall:
    src: str
    name: str
    lineno: int
    reason: str


@dataclass
class ResolveResult:
    edges: list[ResolvedEdge] = field(default_factory=list)
    unresolved: list[UnresolvedCall] = field(default_factory=list)


def build_import_map(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    out: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                out[local] = alias.asname and alias.name or alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                # V0 has no package context here, so relative imports like "from . import x" are skipped.
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                out[local] = f"{node.module}.{alias.name}"
    return out


def _class_for_qualname(qualname: str) -> str | None:
    # Nested classes are represented by keeping everything before the final method segment.
    if "." in qualname:
        return qualname.rsplit(".", 1)[0]
    return None


def _resolve_one(
    fn: ExtractedFunction,
    name: str,
    fn_index: dict[str, ExtractedFunction],
    module_imports: dict[str, str],
) -> tuple[str | None, str]:
    if not name or name == "?":
        return None, "unknown-name"

    parts = name.split(".")
    head = parts[0]

    if head == "self" and fn.is_method and len(parts) == 2:
        cls = _class_for_qualname(fn.qualname)
        if cls is not None:
            candidate = f"{fn.module}:{cls}.{parts[1]}"
            if candidate in fn_index:
                return candidate, ""
        return None, "dynamic-attr"

    if head == "self":
        return None, "dynamic-attr"

    if len(parts) == 1:
        same_mod = f"{fn.module}:{head}"
        if same_mod in fn_index:
            return same_mod, ""
        if head in module_imports:
            target = module_imports[head]
            mod, _, attr = target.rpartition(".")
            if mod:
                return f"{mod}:{attr}", ""
            return f"{target}:__call__", ""
        return None, "unknown-name"

    if head in module_imports:
        target = module_imports[head]
        target_parts = target.split(".")
        if len(target_parts) > 1 and parts[: len(target_parts)] == target_parts:
            rest = ".".join(parts[len(target_parts) :])
            if not rest:
                return None, "dotted-import"
            return f"{target}:{rest}", ""
        rest = ".".join(parts[1:])
        return f"{target}:{rest}", ""

    if f"{fn.module}:{head}" in fn_index or any(k.startswith(f"{fn.module}:{head}.") for k in fn_index):
        return f"{fn.module}:{name}", ""

    return None, "dynamic-attr"


def resolve_calls(
    functions: list[ExtractedFunction],
    fn_index: dict[str, ExtractedFunction],
    imports_by_module: dict[str, dict[str, str]],
) -> ResolveResult:
    result = ResolveResult()
    for fn in functions:
        imports = imports_by_module.get(fn.module, {})
        for cs in fn.call_sites:
            dst, reason = _resolve_one(fn, cs.name, fn_index, imports)
            if dst is None:
                result.unresolved.append(
                    UnresolvedCall(src=fn.id, name=cs.name, lineno=cs.lineno, reason=reason)
                )
            else:
                result.edges.append(ResolvedEdge(src=fn.id, dst=dst, lineno=cs.lineno))
    return result
