"""
Elisp parser utilities for the org-roam database.

This module provides utilities for converting parsed Elisp expressions
to Python objects, specifically tailored for the org-roam database needs.
"""

from pathlib import Path
from typing import Dict, List, Tuple, cast

from org_roam_to_obsidian.elisp import (
    DottedPairExpr,
    ElispParseError,
    Expression,
    ListExpr,
    NumberExpr,
    QuotedExpr,
    StringExpr,
    SymbolExpr,
    parse_elisp,
)


class ParseError(Exception):
    """Exception raised when parsing an Elisp expression fails."""

    pass


def elisp_expr_to_python(expr: Expression) -> object:
    """
    Convert an Elisp expression to a Python object.

    Args:
        expr: An Elisp expression object

    Returns:
        A Python object representing the Elisp expression

    Raises:
        ParseError: If the expression cannot be converted to a Python object
    """
    if isinstance(expr, StringExpr):
        return expr.value
    elif isinstance(expr, NumberExpr):
        return expr.value
    elif isinstance(expr, SymbolExpr):
        return expr.value
    elif isinstance(expr, QuotedExpr):
        return elisp_expr_to_python(expr.expression)
    elif isinstance(expr, ListExpr):
        return [elisp_expr_to_python(element) for element in expr.elements]
    elif isinstance(expr, DottedPairExpr):
        return (elisp_expr_to_python(expr.car), elisp_expr_to_python(expr.cdr))
    else:
        raise ParseError(f"Unsupported expression type: {type(expr).__name__}")


def parse_elisp_string(expr: Expression) -> str:
    """
    Extract a string value from an Elisp expression.

    Args:
        expr: An Elisp expression object

    Returns:
        The string value

    Raises:
        ParseError: If the expression is not a string
    """
    if isinstance(expr, StringExpr):
        return expr.value

    if isinstance(expr, SymbolExpr):
        raise ParseError("Expected string, got str")

    value = elisp_expr_to_python(expr)
    if not isinstance(value, str):
        raise ParseError(f"Expected string, got {type(value).__name__}")
    return value


def parse_elisp_path(expr: Expression) -> Path:
    """
    Extract a file path from an Elisp expression.

    Args:
        expr: An Elisp expression object representing a file path

    Returns:
        A Path object

    Raises:
        ParseError: If the expression is not a valid path
    """
    try:
        path_str = parse_elisp_string(expr)
        return Path(path_str)
    except (ParseError, TypeError) as e:
        raise ParseError(f"Failed to parse path: {e}") from e


def parse_elisp_list(expr: Expression) -> List[object]:
    """
    Extract a list from an Elisp expression.

    Args:
        expr: An Elisp expression object

    Returns:
        A list of Python objects

    Raises:
        ParseError: If the expression is not a list
    """
    value = elisp_expr_to_python(expr)
    if not isinstance(value, list):
        raise ParseError(f"Expected list, got {type(value).__name__}")
    return value


def parse_elisp_plist_to_dict(expr: Expression) -> Dict[str, object]:
    """
    Convert an Elisp property list (plist) to a Python dictionary.

    Elisp plists are lists with alternating keys and values:
    (:key1 value1 :key2 value2)

    Args:
        expr: An Elisp expression object representing a plist

    Returns:
        A dictionary mapping the keys to their values

    Raises:
        ParseError: If the expression is not a valid plist
    """
    values = parse_elisp_list(expr)
    if len(values) % 2 != 0:
        raise ParseError("Property list must have even number of elements")

    parsed_dict: Dict[str, object] = {}
    for i in range(0, len(values), 2):
        key = values[i]
        val = values[i + 1]

        # If the key is a symbol starting with ':', strip the ':'
        if isinstance(key, str) and key.startswith(":"):
            key = key[1:]

        # Ensure key is a string
        key_str = str(key)
        parsed_dict[key_str] = val

    return parsed_dict


def parse_elisp_alist_to_dict(expr: Expression) -> Dict[str, object]:
    """
    Convert an Elisp association list (alist) to a Python dictionary.

    Elisp alists are lists of cons cells (dotted pairs):
    ((key1 . value1) (key2 . value2))

    Args:
        expr: An Elisp expression object representing an alist

    Returns:
        A dictionary mapping the keys to their values

    Raises:
        ParseError: If the expression is not a valid alist
    """
    values = parse_elisp_list(expr)
    parsed_dict: Dict[str, object] = {}

    for i, item in enumerate(values):
        if not isinstance(item, tuple) or len(item) != 2:
            raise ParseError(f"Item at index {i} is not a dotted pair")

        key, val = item
        # Convert key to string if it's not already
        key_str = str(key)
        parsed_dict[key_str] = val

    return parsed_dict


def parse_elisp_time(expr: Expression) -> Tuple[int, int, int, int]:
    """
    Extract a time value from an Elisp expression.

    Elisp time values are stored as a list of four integers:
    (HIGH LOW MICROSEC PICOSEC)

    Args:
        expr: An Elisp expression object representing a time value

    Returns:
        A tuple of (high, low, microsec, picosec)

    Raises:
        ParseError: If the expression is not a valid time value
    """
    values = parse_elisp_list(expr)
    if not values:
        raise ParseError("Empty list cannot be a time value")

    if not all(isinstance(x, (int, float)) for x in values):
        raise ParseError("All elements in time value must be numbers")

    # Extract up to 4 components, filling with zeros if necessary
    components = values + [0] * (4 - len(values))
    # Explicitly cast components to the right types and return a proper tuple
    high = int(cast(float, components[0]))
    low = int(cast(float, components[1]))
    microsec = int(cast(float, components[2]))
    picosec = int(cast(float, components[3]))

    return (high, low, microsec, picosec)


def parse_and_convert_elisp(source: str) -> object:
    """
    Parse Elisp source code and convert it to a Python object.

    This is a convenience function that combines parsing and conversion.

    Args:
        source: The Elisp source code

    Returns:
        A Python object representing the Elisp expression

    Raises:
        ParseError: If parsing or conversion fails
    """
    try:
        expressions = parse_elisp(source)
        if not expressions:
            raise ParseError("No expressions found in input")
        return elisp_expr_to_python(expressions[0])
    except (ElispParseError, ValueError) as e:
        raise ParseError(f"Failed to parse Elisp: {e}") from e
