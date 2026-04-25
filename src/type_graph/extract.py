# src/type_graph/extract.py
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Param:
    name: str
    annotation: str | None


@dataclass(frozen=True)
class CallSite:
    name: str
    lineno: int


@dataclass
class ExtractedFunction:
    id: str
    qualname: str
    module: str
    file: str
    lineno: int
    params: list[Param]
    returns: str | None
    docstring_first_line: str | None
    decorators: list[str]
    is_method: bool
    is_async: bool
    call_sites: list[CallSite] = field(default_factory=list)
    body_hash: str = ""


def _annotation_to_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    return ast.unparse(node)


def _decorator_to_str(node: ast.expr) -> str:
    return ast.unparse(node)


def _call_target(node: ast.Call) -> str | None:
    f = node.func
    try:
        return ast.unparse(f)
    except Exception:
        return None


def _call_sites_in_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[CallSite]:
    calls: list[CallSite] = []
    for stmt in node.body:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Call):
                calls.append(CallSite(name=_call_target(child) or "?", lineno=child.lineno))
    return calls


def _docstring_first_line(node: ast.AST) -> str | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return first.value.value.strip().splitlines()[0] if first.value.value.strip() else None
    return None


def _hash_body(node: ast.AST) -> str:
    return hashlib.sha1(ast.dump(node).encode()).hexdigest()


def extract_functions(path: Path, *, module: str) -> list[ExtractedFunction]:
    tree = ast.parse(path.read_text(), filename=str(path))
    out: list[ExtractedFunction] = []

    def visit(node: ast.AST, qual_prefix: str, in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{qual_prefix}{child.name}" if qual_prefix else child.name
                params = [
                    Param(a.arg, _annotation_to_str(a.annotation))
                    for a in child.args.args
                ]
                calls = _call_sites_in_body(child)
                out.append(
                    ExtractedFunction(
                        id=f"{module}:{qual}",
                        qualname=qual,
                        module=module,
                        file=str(path),
                        lineno=child.lineno,
                        params=params,
                        returns=_annotation_to_str(child.returns),
                        docstring_first_line=_docstring_first_line(child),
                        decorators=[_decorator_to_str(d) for d in child.decorator_list],
                        is_method=in_class,
                        is_async=isinstance(child, ast.AsyncFunctionDef),
                        call_sites=calls,
                        body_hash=_hash_body(child),
                    )
                )
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{qual_prefix}{child.name}.", in_class=True)

    visit(tree, "", in_class=False)
    return out
