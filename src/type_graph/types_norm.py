# src/type_graph/types_norm.py
from __future__ import annotations


def normalize_annotation(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    # Triple-quoted strings are only partially unquoted; AST annotations do not produce them in v0.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s
