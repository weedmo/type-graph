# tests/test_resolve.py
from pathlib import Path
import textwrap

from type_graph.extract import extract_functions
from type_graph.resolve import build_import_map, resolve_calls


def write_py(p: Path, body: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body).lstrip())
    return p


def test_import_map(tmp_path: Path) -> None:
    p = write_py(tmp_path / "m.py", '''
        import os
        import numpy as np
        from pkg.sub import foo as bar
        from pkg import baz
    ''')
    imports = build_import_map(p)
    assert imports == {
        "os": "os",
        "np": "numpy",
        "bar": "pkg.sub.foo",
        "baz": "pkg.baz",
    }


def test_resolves_same_module_call(tmp_path: Path) -> None:
    p = write_py(tmp_path / "m.py", '''
        def helper():
            return 1
        def main():
            helper()
    ''')
    funcs = extract_functions(p, module="m")
    fn_index = {f.id: f for f in funcs}
    resolved = resolve_calls(funcs, fn_index, imports_by_module={"m": {}})
    main_edges = [e for e in resolved.edges if e.src == "m:main"]
    assert main_edges and main_edges[0].dst == "m:helper"
    assert resolved.unresolved == []


def test_resolves_imported_call(tmp_path: Path) -> None:
    p = write_py(tmp_path / "m.py", '''
        from pkg import helper
        def main():
            helper(1)
    ''')
    funcs = extract_functions(p, module="m")
    imports = {"m": build_import_map(p)}
    resolved = resolve_calls(funcs, fn_index={f.id: f for f in funcs}, imports_by_module=imports)
    edges = [e for e in resolved.edges if e.src == "m:main"]
    assert edges and edges[0].dst == "pkg:helper"


def test_records_unresolved_dynamic_attr(tmp_path: Path) -> None:
    p = write_py(tmp_path / "m.py", '''
        def main():
            self.something()
    ''')
    funcs = extract_functions(p, module="m")
    resolved = resolve_calls(funcs, fn_index={f.id: f for f in funcs}, imports_by_module={"m": {}})
    assert resolved.edges == []
    assert any(u.reason == "dynamic-attr" for u in resolved.unresolved)


def test_resolves_self_method_inside_class(tmp_path: Path) -> None:
    p = write_py(tmp_path / "m.py", '''
        class C:
            def helper(self):
                return 1
            def main(self):
                self.helper()
    ''')
    funcs = extract_functions(p, module="m")
    resolved = resolve_calls(funcs, fn_index={f.id: f for f in funcs}, imports_by_module={"m": {}})
    edges = [e for e in resolved.edges if e.src == "m:C.main"]
    assert edges and edges[0].dst == "m:C.helper"
