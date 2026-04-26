# tests/test_query.py
import json
from pathlib import Path

from type_graph.cli import main
from type_graph.llm import AnthropicClient
from type_graph.pipeline import run
from type_graph.query import explain, query, shortest_call_path


FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def _ensure_graph(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    run(root=FIXTURE, out_dir=out, llm_client=None, infer=False, cluster_depth=3,
        include_tests=False, excludes=[], no_html=True)
    return out / "graph.json"


def test_explain_prints_signature_and_callers(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    explain("sample_repo.models:normalize_name", graph_path=graph)
    out = capsys.readouterr().out
    assert "normalize_name" in out
    assert "Callers:" in out and "sample_repo.api:make_user" in out


def test_shortest_call_path(tmp_path: Path) -> None:
    graph = _ensure_graph(tmp_path)
    chain = shortest_call_path(
        "sample_repo.api:make_user",
        "sample_repo.models:normalize_name",
        graph_path=graph,
    )
    assert chain == ["sample_repo.api:make_user", "sample_repo.models:normalize_name"]


def test_cli_path_subcommand_prints_chain(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    rc = main(["path", "sample_repo.api:make_user", "sample_repo.models:normalize_name", str(graph)])
    assert rc == 0
    assert "sample_repo.api:make_user -> sample_repo.models:normalize_name" in capsys.readouterr().out


def test_cli_query_no_llm_returns_3(tmp_path: Path, capsys) -> None:
    graph = _ensure_graph(tmp_path)
    rc = main(["query", "what calls normalize_name?", str(graph), "--no-llm"])
    assert rc == 3
    assert "requires an LLM client" in capsys.readouterr().err


def test_query_asks_llm_question_with_graph_context(tmp_path: Path, capsys) -> None:
    class RecordingClient:
        question: str | None = None
        context: str | None = None

        def answer_question(self, question: str, context: str) -> str:
            self.question = question
            self.context = context
            return "normalize_name is called by make_user."

        def summarize_function(self, name: str, body_excerpt: str) -> str:
            raise AssertionError("query should call answer_question")

    graph = _ensure_graph(tmp_path)
    client = RecordingClient()

    rc = query("what calls normalize_name?", graph_path=graph, client=client)

    assert rc == 0
    assert capsys.readouterr().out.strip() == "normalize_name is called by make_user."
    assert client.question == "what calls normalize_name?"
    assert client.context is not None
    assert "Clusters:" in client.context
    assert "A few function names:" in client.context
    assert "make_user" in client.context
    assert "Question:" not in client.context


def test_anthropic_answer_question_uses_larger_token_budget_than_summaries() -> None:
    class TextBlock:
        type = "text"
        text = "paragraph answer"

    class MessageResponse:
        content = [TextBlock()]

    class Messages:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return MessageResponse()

    class StubAnthropic:
        def __init__(self) -> None:
            self.messages = Messages()

    stub = StubAnthropic()
    client = AnthropicClient(model="test-model")
    client._client = stub

    assert client.summarize_function("normalize_name", "return name.strip()") == "paragraph answer"
    assert client.answer_question("what calls normalize_name?", "Context") == "paragraph answer"

    summary_call, question_call = stub.messages.calls
    assert summary_call["max_tokens"] == 80
    assert question_call["max_tokens"] == 512
    assert "what calls normalize_name?" in question_call["messages"][0]["content"]
    assert "Context" in question_call["messages"][0]["content"]
