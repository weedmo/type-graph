# src/type_graph/cli.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from type_graph.llm import AnthropicClient
from type_graph.pipeline import run


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="type-graph")
    p.add_argument("path", nargs="?", type=Path)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--infer", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--no-html", action="store_true")
    p.add_argument("--cluster-depth", type=int, default=3)
    p.add_argument("--include-tests", action="store_true")
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--update", action="store_true")
    p.add_argument("--open", dest="open_html", action="store_true")
    p.add_argument("--yes", action="store_true")
    return p


def _maybe_dispatch_subcommand(argv: list[str] | None) -> int | None:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        return None
    head = raw[0]
    if head not in {"explain", "path", "query"}:
        return None

    if head == "explain":
        if len(raw) < 2:
            print("usage: type-graph explain <function_id> [graph.json]", file=sys.stderr)
            return 3
        function_id = raw[1]
        # Default graph path is relative to the current working directory.
        graph = Path(raw[2]) if len(raw) > 2 else Path("type-graph-out/graph.json")
        from type_graph.query import explain
        return explain(function_id, graph_path=graph)

    if head == "path":
        if len(raw) < 3:
            print("usage: type-graph path <a> <b> [graph.json]", file=sys.stderr)
            return 3
        a, b = raw[1], raw[2]
        # Default graph path is relative to the current working directory.
        graph = Path(raw[3]) if len(raw) > 3 else Path("type-graph-out/graph.json")
        from type_graph.query import shortest_call_path
        chain = shortest_call_path(a, b, graph_path=graph)
        print(" -> ".join(chain) if chain else "no path")
        return 0

    if head == "query":
        no_llm = "--no-llm" in raw
        args = [a for a in raw[1:] if a != "--no-llm"]
        if not args:
            print('usage: type-graph query "<question>" [graph.json] [--no-llm]', file=sys.stderr)
            return 3
        question = args[0]
        # Default graph path is relative to the current working directory.
        graph = Path(args[1]) if len(args) > 1 else Path("type-graph-out/graph.json")
        from type_graph.llm import AnthropicClient as _AnthropicClient
        from type_graph.query import query as run_query
        return run_query(question, graph_path=graph, client=None if no_llm else _AnthropicClient())

    return None


def main(argv: list[str] | None = None) -> int:
    subcommand_rc = _maybe_dispatch_subcommand(argv)
    if subcommand_rc is not None:
        return subcommand_rc

    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "analyze":
        raw = raw[1:]
    args = _build_parser().parse_args(raw)
    if not args.path:
        print("usage: type-graph <path> [options]", file=sys.stderr)
        return 3
    if args.open_html and args.no_html:
        print("type-graph: --open cannot be used with --no-html", file=sys.stderr)
        return 3

    out = args.out or (args.path.resolve() / "type-graph-out")

    if args.update:
        from type_graph.update import run_update
        return run_update(
            root=args.path, out_dir=out,
            llm_client=None,
            llm_client_factory=None if args.no_llm else AnthropicClient,
            infer=args.infer, cluster_depth=args.cluster_depth,
            include_tests=args.include_tests, excludes=args.exclude,
            no_html=args.no_html,
        )

    rc = run(
        root=args.path, out_dir=out,
        llm_client=None,
        llm_client_factory=None if args.no_llm else AnthropicClient,
        infer=args.infer, cluster_depth=args.cluster_depth,
        include_tests=args.include_tests, excludes=args.exclude,
        no_html=args.no_html,
    )

    if args.open_html and rc == 0:
        import webbrowser
        webbrowser.open((out / "graph.html").as_uri())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
