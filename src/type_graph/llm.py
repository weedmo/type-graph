# src/type_graph/llm.py
from __future__ import annotations

import os
from typing import Protocol


class LLMClient(Protocol):
    def summarize_function(self, name: str, body_excerpt: str) -> str: ...
    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str: ...
    def answer_question(self, question: str, context: str) -> str: ...


class AnthropicClient:
    """Real client. Constructed lazily so tests don't need ANTHROPIC_API_KEY."""

    def __init__(self, model: str | None = None) -> None:
        self._client = None
        self._model = model

    def _ask(self, prompt: str, *, max_tokens: int = 80) -> str:
        model = self._model or os.environ.get("TYPE_GRAPH_ANTHROPIC_MODEL")
        if not model:
            raise RuntimeError("Set TYPE_GRAPH_ANTHROPIC_MODEL or pass model explicitly")
        if self._client is None:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic()
            self._model = model

        msg = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()

    def summarize_function(self, name: str, body_excerpt: str) -> str:
        return self._ask(
            "Write ONE short imperative sentence describing what this Python function does. "
            f"Function: {name}\nBody:\n{body_excerpt}"
        )

    def summarize_cluster(self, cluster_id: str, function_lines: list[str]) -> str:
        joined = "\n".join(function_lines[:30])
        return self._ask(
            "Write ONE short sentence summarizing this cluster of related Python functions. "
            f"Cluster id: {cluster_id}\nFunctions:\n{joined}"
        )

    def answer_question(self, question: str, context: str) -> str:
        return self._ask(
            "Answer the user's question using only the type-graph context. "
            "Answer in one short paragraph.\n\n"
            f"Question: {question}\n\nContext:\n{context}",
            max_tokens=512,
        )
