# src/type_graph/label.py
from __future__ import annotations

from typing import Mapping

from type_graph.build import GraphPayload
from type_graph.llm import LLMClient


def label_payload(
    payload: GraphPayload,
    *,
    client: LLMClient | None,
    cached_roles: Mapping[str, tuple[str, str, str]] | None = None,
) -> None:
    by_id = {f["id"]: f for f in payload.functions}
    cached_roles = cached_roles or {}

    for f in payload.functions:
        if f.get("role_source") != "missing":
            continue
        cached = cached_roles.get(f["id"])
        if cached and cached[0] == f.get("hash") and cached[1] and cached[2] not in {"missing", "failed"}:
            f["role"] = cached[1]
            f["role_source"] = cached[2]
            continue
        if client is None:
            continue
        excerpt = f"{f['qualname']} at {f.get('file', '')}:{f.get('lineno', '')}"
        try:
            f["role"] = client.summarize_function(f["qualname"], excerpt)
            f["role_source"] = "llm"
        except Exception:
            f["role"] = ""
            f["role_source"] = "failed"

    if client is None:
        return

    for c in payload.clusters:
        lines = [
            f"- {by_id[fid]['qualname']}: {by_id[fid].get('role', '') or '?'}"
            for fid in c.get("function_ids", [])
            if fid in by_id
        ]
        if not lines:
            continue
        try:
            c["summary"] = client.summarize_cluster(c["id"], lines)
        except Exception:
            c["summary"] = ""
            c["summary_source"] = "failed"
