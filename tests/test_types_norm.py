# tests/test_types_norm.py
from type_graph.types_norm import normalize_annotation


def test_strips_whitespace() -> None:
    assert normalize_annotation("  int  ") == "int"


def test_unquotes_string_annotation() -> None:
    assert normalize_annotation("'List[int]'") == "List[int]"
    assert normalize_annotation('"dict[str, Tensor]"') == "dict[str, Tensor]"


def test_partially_unquotes_triple_quoted_string() -> None:
    assert normalize_annotation('"""foo"""') == '""foo""'


def test_returns_none_for_none() -> None:
    assert normalize_annotation(None) is None


def test_returns_none_for_empty_string() -> None:
    assert normalize_annotation("") is None


def test_keeps_complex_form() -> None:
    assert normalize_annotation("Callable[[int], int]") == "Callable[[int], int]"
