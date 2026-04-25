# tests/test_extract.py
import ast
import hashlib
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


def test_extracts_property_static_class_and_async_methods(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        class C:
            @property
            def value(self) -> int:
                return 1

            @staticmethod
            def make(x: str) -> str:
                return x

            @classmethod
            async def load(cls):
                return cls()
    ''')
    funcs = extract_functions(p, module="m")
    by_qualname = {f.qualname: f for f in funcs}
    assert [f.qualname for f in funcs] == ["C.value", "C.make", "C.load"]
    assert all(f.is_method for f in funcs)
    assert by_qualname["C.value"].decorators == ["property"]
    assert by_qualname["C.make"].decorators == ["staticmethod"]
    assert by_qualname["C.load"].decorators == ["classmethod"]
    assert by_qualname["C.load"].is_async is True


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


def test_docstring_first_line_ignores_class_and_nonfirst_string_literals(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        class C:
            "Class docstring only."

            def f(self):
                value = 1
                "not a function docstring"
                return value

        def g():
            """Function docstring."""
            return 1
    ''')
    funcs = extract_functions(p, module="m")
    by_qualname = {f.qualname: f for f in funcs}
    assert by_qualname["C.f"].docstring_first_line is None
    assert by_qualname["g"].docstring_first_line == "Function docstring."


def test_body_hash_uses_sha1_with_usedforsecurity_false(tmp_path: Path, monkeypatch) -> None:
    p = write_py(tmp_path, "m.py", '''
        def f():
            return 1
    ''')
    seen: dict[str, object] = {}
    real_sha1 = hashlib.sha1

    def fake_sha1(data: bytes = b"", *args: object, **kwargs: object):
        seen["usedforsecurity"] = kwargs.get("usedforsecurity")
        return real_sha1(data, *args, **kwargs)

    monkeypatch.setattr(hashlib, "sha1", fake_sha1)
    extract_functions(p, module="m")
    assert seen["usedforsecurity"] is False


def test_extracts_full_parameter_list(tmp_path: Path) -> None:
    p = write_py(tmp_path, "m.py", '''
        def f(a: int, /, b: str, *args: float, kw: bool, **kwargs: object) -> None:
            pass
    ''')
    funcs = extract_functions(p, module="m")
    assert [param.name for param in funcs[0].params] == [
        "a",
        "b",
        "*args",
        "kw",
        "**kwargs",
    ]
    assert [param.annotation for param in funcs[0].params] == [
        "int",
        "str",
        "float",
        "bool",
        "object",
    ]


def test_skips_call_site_when_target_cannot_be_unparsed(tmp_path: Path, monkeypatch) -> None:
    p = write_py(tmp_path, "m.py", '''
        def f():
            bad()
    ''')
    real_unparse = ast.unparse

    def fake_unparse(node: ast.AST) -> str:
        if isinstance(node, ast.Name) and node.id == "bad":
            raise ValueError("cannot unparse")
        return real_unparse(node)

    monkeypatch.setattr(ast, "unparse", fake_unparse)
    funcs = extract_functions(p, module="m")
    assert funcs[0].call_sites == []
