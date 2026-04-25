# tests/test_extract.py
from pathlib import Path
import textwrap

from type_graph.extract import extract_functions, ExtractedFunction


def write_py(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body).lstrip())
    return p


def test_extracts_module_function(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        def add(a: int, b: int) -> int:
            """Add two ints."""
            return a + b
    ''')
    funcs = extract_functions(p, module="m")
    assert len(funcs) == 1
    f = funcs[0]
    assert isinstance(f, ExtractedFunction)
    assert f.qualname == "add"
    assert f.id == "m:add"
    assert f.docstring_first_line == "Add two ints."
    assert [pp.name for pp in f.params] == ["a", "b"]
    assert [pp.annotation for pp in f.params] == ["int", "int"]
    assert f.returns == "int"
    assert f.is_method is False


def test_extracts_methods(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        class C:
            def f(self, x: str) -> bool:
                return bool(x)
    ''')
    funcs = extract_functions(p, module="m")
    assert [f.id for f in funcs] == ["m:C.f"]
    assert funcs[0].is_method is True
    assert funcs[0].qualname == "C.f"


def test_extracts_async_and_decorators(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        import functools
        @functools.cache
        async def g(x: int) -> int:
            return x
    ''')
    funcs = extract_functions(p, module="m")
    assert funcs[0].is_async is True
    assert funcs[0].decorators == ["functools.cache"]


def test_skips_lambdas(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", "h = lambda x: x\n")
    assert extract_functions(p, module="m") == []


def test_collects_call_names(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        def a():
            b()
            obj.c(1)
    ''')
    funcs = extract_functions(p, module="m")
    names = [c.name for c in funcs[0].call_sites]
    assert "b" in names
    assert "obj.c" in names


def test_ignores_decorator_factory_calls(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        def decorator_factory():
            def wrap(fn):
                return fn
            return wrap

        @decorator_factory()
        def decorated():
            return helper()
    ''')
    funcs = extract_functions(p, module="m")
    decorated = next(f for f in funcs if f.qualname == "decorated")
    names = [c.name for c in decorated.call_sites]
    assert names == ["helper"]
