"""Tests for the elisp parser."""

import pytest

from org_roam_to_obsidian.elisp import (
    DottedPairExpr,
    ElispParseError,
    ListExpr,
    NumberExpr,
    QuotedExpr,
    StringExpr,
    SymbolExpr,
    parse_elisp,
)


@pytest.mark.parametrize(
    "input_str,expected",
    [
        # Symbol expressions
        ("symbol", [SymbolExpr("symbol")]),
        ("symbol1 symbol2", [SymbolExpr("symbol1"), SymbolExpr("symbol2")]),
        ("nil", [SymbolExpr("nil")]),
        ("t", [SymbolExpr("t")]),
        # Number expressions
        ("42", [NumberExpr(42)]),
        ("-10", [NumberExpr(-10)]),
        ("3.14", [NumberExpr(3.14)]),
        ("-2.5", [NumberExpr(-2.5)]),
        ("1 2 3", [NumberExpr(1), NumberExpr(2), NumberExpr(3)]),
        # String expressions
        ('"hello"', [StringExpr("hello")]),
        ('"hello world"', [StringExpr("hello world")]),
        ('"escaped \\"quotes\\""', [StringExpr('escaped "quotes"')]),
        # Empty lists
        ("()", [ListExpr([])]),
        ("() ()", [ListExpr([]), ListExpr([])]),
        # List expressions
        ("(a b c)", [ListExpr([SymbolExpr("a"), SymbolExpr("b"), SymbolExpr("c")])]),
        (
            "(1 2 3)",
            [ListExpr([NumberExpr(1), NumberExpr(2), NumberExpr(3)])],
        ),
        (
            '(symbol "string" 42)',
            [ListExpr([SymbolExpr("symbol"), StringExpr("string"), NumberExpr(42)])],
        ),
        # Quoted expressions
        ("'symbol", [QuotedExpr(SymbolExpr("symbol"))]),
        ("'42", [QuotedExpr(NumberExpr(42))]),
        (
            "'(a b c)",
            [QuotedExpr(ListExpr([SymbolExpr("a"), SymbolExpr("b"), SymbolExpr("c")]))],
        ),
        # Nested expressions
        (
            "(outer (inner1 inner2) outer2)",
            [
                ListExpr(
                    [
                        SymbolExpr("outer"),
                        ListExpr([SymbolExpr("inner1"), SymbolExpr("inner2")]),
                        SymbolExpr("outer2"),
                    ]
                )
            ],
        ),
        (
            "(a (b (c (d))))",
            [
                ListExpr(
                    [
                        SymbolExpr("a"),
                        ListExpr(
                            [
                                SymbolExpr("b"),
                                ListExpr(
                                    [SymbolExpr("c"), ListExpr([SymbolExpr("d")])]
                                ),
                            ]
                        ),
                    ]
                )
            ],
        ),
        # Dotted pair expressions
        ("(a . b)", [DottedPairExpr(SymbolExpr("a"), SymbolExpr("b"))]),
        (
            "(a . (b c))",
            [
                DottedPairExpr(
                    SymbolExpr("a"), ListExpr([SymbolExpr("b"), SymbolExpr("c")])
                )
            ],
        ),
        # Comments
        (";; This is a comment\nsymbol", [SymbolExpr("symbol")]),
        ("symbol ;; comment", [SymbolExpr("symbol")]),
        (
            "(a b) ;; comment\n(c d)",
            [
                ListExpr([SymbolExpr("a"), SymbolExpr("b")]),
                ListExpr([SymbolExpr("c"), SymbolExpr("d")]),
            ],
        ),
    ],
)
def test_parse_elisp(input_str, expected):
    """Parse elisp expressions and compare with expected results."""
    result = parse_elisp(input_str)
    assert result == expected


@pytest.mark.parametrize(
    "input_str,error",
    [
        ("(", ElispParseError),  # Unclosed list
        (")", ElispParseError),  # Unexpected right paren
        ("(a . b . c)", ElispParseError),  # Invalid dotted pair
        ("(a . )", ElispParseError),  # Invalid dotted pair
        ("(a b . c d)", ElispParseError),  # Expected ) after dotted pair
    ],
)
def test_parse_elisp_errors(input_str, error):
    """Test parser error handling with invalid input."""
    with pytest.raises(error):
        parse_elisp(input_str)
