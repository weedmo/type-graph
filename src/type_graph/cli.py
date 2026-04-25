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


def main(argv: list[str] | None = None) -> int:
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
            llm_client=None if args.no_llm else AnthropicClient(),
            infer=args.infer, cluster_depth=args.cluster_depth,
            include_tests=args.include_tests, excludes=args.exclude,
            no_html=args.no_html,
        )

    rc = run(
        root=args.path, out_dir=out,
        llm_client=None if args.no_llm else AnthropicClient(),
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
