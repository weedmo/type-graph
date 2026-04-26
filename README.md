# type-graph

Function-level type and call graph for Python codebases.

`type-graph` turns a Python project into a navigable ROS-`rqt_graph`-style
visualization where:

- Functions are nodes carrying their input/output type signatures.
- Calls are directed edges; `passed_types` is present in `graph.json` and remains empty in v0.
- Module/package prefixes form clusters; an LLM writes a one-line summary per cluster.

## Install

```bash
pip install -e .
# Optional: Pyright diagnostics mode
pip install -e ".[infer]"
```

## Use

```bash
type-graph path/to/repo                 # analyze
type-graph path/to/repo --infer         # run Pyright diagnostics
type-graph path/to/repo --no-llm        # docstring-only roles
type-graph path/to/repo --update        # incremental (only changed files)
type-graph path/to/repo --open          # open graph.html after rendering

type-graph explain <fn_id>              # signature + role + neighbors
type-graph path <a> <b>                 # shortest call path
type-graph query "<question>"           # natural-language Q over the graph
```

Outputs land in `type-graph-out/`:

- `graph.json` — single source of truth.
- `graph.html` — self-contained, opens anywhere.
- `REPORT.md` — cluster summaries and honesty statistics.
- `manifest.json` — per-file hashes used by `--update`.
