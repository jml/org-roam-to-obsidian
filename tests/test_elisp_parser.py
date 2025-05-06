"""Tests for the elisp_parser module."""

from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from org_roam_to_obsidian.elisp import (
    DottedPairExpr,
    Expression,
    ListExpr,
    NumberExpr,
    QuotedExpr,
    StringExpr,
    SymbolExpr,
    parse_elisp,
)
from org_roam_to_obsidian.elisp_parser import (
    ParseError,
    elisp_expr_to_python,
    parse_and_convert_elisp,
    parse_elisp_alist_to_dict,
    parse_elisp_list,
    parse_elisp_path,
    parse_elisp_plist_to_dict,
    parse_elisp_string,
    parse_elisp_time,
)


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ('"test"', "test"),
        ("42", 42),
        ("42.5", 42.5),
        ("symbol", "symbol"),
        ("(1 2 3)", [1, 2, 3]),
        ("'(1 2 3)", [1, 2, 3]),
        ("(1 . 2)", (1, 2)),
        ("((a . 1) (b . 2))", [("a", 1), ("b", 2)]),
        ("(:key1 value1 :key2 42)", [":key1", "value1", ":key2", 42]),
        ("(25821 50943 0 0)", [25821, 50943, 0, 0]),
        ('"/path/to/file.org"', "/path/to/file.org"),
        ("()", []),
    ],
)
def test_parse_and_convert_elisp(elisp_str: str, expected: object) -> None:
    result = parse_and_convert_elisp(elisp_str)
    assert result == expected


def test_parse_and_convert_elisp_errors() -> None:
    with pytest.raises(ParseError, match="No expressions found in input"):
        parse_and_convert_elisp("")

    with pytest.raises(ParseError, match="Failed to parse Elisp"):
        parse_and_convert_elisp("(invalid syntax")


@pytest.mark.parametrize(
    "expr, expected",
    [
        (StringExpr("test"), "test"),
        (NumberExpr(42), 42),
        (NumberExpr(42.5), 42.5),
        (SymbolExpr("symbol"), "symbol"),
        (ListExpr([NumberExpr(1), NumberExpr(2), NumberExpr(3)]), [1, 2, 3]),
        (QuotedExpr(ListExpr([NumberExpr(1), NumberExpr(2)])), [1, 2]),
        (DottedPairExpr(NumberExpr(1), NumberExpr(2)), (1, 2)),
    ],
)
def test_elisp_expr_to_python(expr: Expression, expected: object) -> None:
    result = elisp_expr_to_python(expr)
    assert result == expected


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ('"test"', "test"),
        ('"path/to/file"', "path/to/file"),
        ('"with \\"quotes\\""', 'with "quotes"'),
    ],
)
def test_parse_elisp_string(elisp_str: str, expected: str) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_string(expr)
    assert result == expected


def test_parse_elisp_string_errors() -> None:
    with pytest.raises(ParseError, match="Expected string, got int"):
        parse_elisp_string(NumberExpr(42))

    with pytest.raises(ParseError, match="Expected string, got str"):
        parse_elisp_string(SymbolExpr("symbol"))


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ('"/path/to/file.org"', Path("/path/to/file.org")),
        ('"file.org"', Path("file.org")),
        ('"/"', Path("/")),
    ],
)
def test_parse_elisp_path(elisp_str: str, expected: Path) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_path(expr)
    assert result == expected


def test_parse_elisp_path_errors() -> None:
    with pytest.raises(ParseError, match="Failed to parse path"):
        parse_elisp_path(NumberExpr(42))


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ("(1 2 3)", [1, 2, 3]),
        ('("a" "b" "c")', ["a", "b", "c"]),
        ("(symbol1 symbol2)", ["symbol1", "symbol2"]),
        ('(1 "string" symbol)', [1, "string", "symbol"]),
        ("()", []),
    ],
)
def test_parse_elisp_list(elisp_str: str, expected: List[object]) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_list(expr)
    assert result == expected


def test_parse_elisp_list_errors() -> None:
    with pytest.raises(ParseError, match="Expected list, got int"):
        parse_elisp_list(NumberExpr(42))

    with pytest.raises(ParseError, match="Expected list, got str"):
        parse_elisp_list(StringExpr("not a list"))


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ("(:key1 value1 :key2 42)", {"key1": "value1", "key2": 42}),
        ("(:a 1 :b 2 :c 3)", {"a": 1, "b": 2, "c": 3}),
        ('(:name "John" :age 30)', {"name": "John", "age": 30}),
        ("(key1 value1 key2 value2)", {"key1": "value1", "key2": "value2"}),
        ("()", {}),  # Empty list is a valid empty property list
    ],
)
def test_parse_elisp_plist_to_dict(elisp_str: str, expected: Dict[str, object]) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_plist_to_dict(expr)
    assert result == expected


def test_parse_elisp_plist_to_dict_errors() -> None:
    with pytest.raises(ParseError, match="Expected list, got int"):
        parse_elisp_plist_to_dict(NumberExpr(42))

    with pytest.raises(
        ParseError, match="Property list must have even number of elements"
    ):
        expr = parse_elisp("(:key1 value1 :key2)")[0]
        parse_elisp_plist_to_dict(expr)


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ("((a . 1) (b . 2))", {"a": 1, "b": 2}),
        ('((name . "John") (age . 30))', {"name": "John", "age": 30}),
        ("((1 . a) (2 . b))", {"1": "a", "2": "b"}),
        ("()", {}),  # Empty list is a valid empty alist
    ],
)
def test_parse_elisp_alist_to_dict(elisp_str: str, expected: Dict[str, object]) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_alist_to_dict(expr)
    assert result == expected


def test_parse_elisp_alist_to_dict_errors() -> None:
    with pytest.raises(ParseError, match="Expected list, got int"):
        parse_elisp_alist_to_dict(NumberExpr(42))

    with pytest.raises(ParseError, match="Item at index 0 is not a dotted pair"):
        expr = parse_elisp("(not-dotted-pair)")[0]
        parse_elisp_alist_to_dict(expr)


@pytest.mark.parametrize(
    "elisp_str, expected",
    [
        ("(25821 50943 0 0)", (25821, 50943, 0, 0)),
        ("(25821 50943)", (25821, 50943, 0, 0)),  # Fills missing values with 0
        ("(25821)", (25821, 0, 0, 0)),  # Fills missing values with 0
        ("(25821 50943 100 200)", (25821, 50943, 100, 200)),
    ],
)
def test_parse_elisp_time(elisp_str: str, expected: Tuple[int, int, int, int]) -> None:
    expr = parse_elisp(elisp_str)[0]
    result = parse_elisp_time(expr)
    assert result == expected


def test_parse_elisp_time_errors() -> None:
    with pytest.raises(ParseError, match="Expected list, got int"):
        parse_elisp_time(NumberExpr(42))

    with pytest.raises(ParseError, match="Empty list cannot be a time value"):
        expr = parse_elisp("()")[0]
        parse_elisp_time(expr)

    with pytest.raises(ParseError, match="All elements in time value must be numbers"):
        expr = parse_elisp("(a b c d)")[0]
        parse_elisp_time(expr)
