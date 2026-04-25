# tests/test_modules.py
from pathlib import Path
from type_graph.modules import path_to_module


def test_top_level_file() -> None:
    assert path_to_module(Path("a.py")) == "a"


def test_nested_module() -> None:
    assert path_to_module(Path("pkg/sub/b.py")) == "pkg.sub.b"


def test_init_collapses_to_package() -> None:
    assert path_to_module(Path("pkg/__init__.py")) == "pkg"
    assert path_to_module(Path("pkg/sub/__init__.py")) == "pkg.sub"


def test_package_root_prefix() -> None:
    assert path_to_module(Path("models.py"), root_package="sample_repo") == "sample_repo.models"
    assert path_to_module(Path("__init__.py"), root_package="sample_repo") == "sample_repo"
