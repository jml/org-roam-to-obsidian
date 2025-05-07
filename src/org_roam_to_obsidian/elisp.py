"""
Elisp Expression Parser

A clean, simple, strongly typed Python 3 module for parsing Elisp expressions.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List, Optional, Union


class TokenType(Enum):
    """Token types for Elisp expressions."""

    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    SYMBOL = auto()
    NUMBER = auto()
    STRING = auto()
    QUOTE = auto()
    DOT = auto()
    COMMENT = auto()


@dataclass(frozen=True)
class Token:
    """Represents a lexical token."""

    type: TokenType
    value: str
    position: int


@dataclass
class ElispParseError(Exception):
    """Custom exception for Elisp parsing errors that includes token information."""

    message: str
    tokens: list[Token]
    position: int

    def __str__(self) -> str:
        """Format the error message with context from tokens and position."""
        result = [self.message]

        if self.tokens:
            # Reconstruct the string being parsed
            source = ""
            if len(self.tokens) > 0:
                # Sort tokens by position to ensure correct order
                sorted_tokens = sorted(self.tokens, key=lambda t: t.position)

                # Get the original source from token positions and values
                last_pos = 0
                for token in sorted_tokens:
                    # Add any spaces or characters between tokens
                    if token.position > last_pos:
                        source += " " * (token.position - last_pos)

                    source += token.value
                    last_pos = token.position + len(token.value)

            result.append(f"\nInput: {source}")

            # Create a pointer to the position of the error
            if self.position is not None:
                pointer = " " * (len("Input: ") + self.position) + "^"
                result.append(pointer)

        return "\n".join(result)


def tokenize(source: str) -> Iterator[Token]:
    """
    Tokenize an Elisp expression string.

    Args:
        source: The Elisp source code to tokenize

    Yields:
        Token objects representing the lexical elements
    """
    # Token patterns
    patterns = {
        TokenType.COMMENT: r";[^\n]*",
        TokenType.STRING: r'"(?:\\.|[^"\\])*"',
        TokenType.NUMBER: r"-?[0-9]+(?:\.[0-9]+)?",
        TokenType.LEFT_PAREN: r"\(",
        TokenType.RIGHT_PAREN: r"\)",
        TokenType.QUOTE: r"'",
        TokenType.DOT: r"\.",
        TokenType.SYMBOL: r"[^\s()'\"]+",
    }

    # Combine all patterns
    pattern = "|".join(
        f"(?P<{token_type.name}>{pattern})" for token_type, pattern in patterns.items()
    )
    regex = re.compile(pattern)

    position = 0
    for match in regex.finditer(source):
        for name, value in match.groupdict().items():
            if value is not None:
                token_type = getattr(TokenType, name)
                if token_type != TokenType.COMMENT:  # Skip comments
                    yield Token(token_type, value, position)
                position = match.end()
                break


Symbol = str
Number = Union[int, float]
String = str


class Expression:
    pass


@dataclass(frozen=True)
class SymbolExpr(Expression):
    """Represents a symbol expression."""

    value: Symbol


@dataclass(frozen=True)
class NumberExpr(Expression):
    """Represents a numeric expression."""

    value: Number


@dataclass(frozen=True)
class StringExpr(Expression):
    """Represents a string expression."""

    value: String


@dataclass(frozen=True)
class ListExpr(Expression):
    """Represents a list expression."""

    elements: List[Expression]


@dataclass(frozen=True)
class QuotedExpr(Expression):
    """Represents a quoted expression."""

    expression: Expression


@dataclass(frozen=True)
class DottedPairExpr(Expression):
    """Represents a dotted pair (improper list)."""

    car: Expression
    cdr: Expression


@dataclass
class Parser:
    """Parser for Elisp expressions."""

    tokens: list[Token]
    current: int = 0

    def peek(self) -> Optional[Token]:
        """Look at the current token without consuming it."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return None

    def advance(self) -> Optional[Token]:
        """Consume and return the current token."""
        if self.current < len(self.tokens):
            token = self.tokens[self.current]
            self.current += 1
            return token
        return None

    def parse_expression(self) -> Expression:
        """Parse a single expression."""
        token = self.advance()

        if token is None:
            raise ElispParseError(
                message="Unexpected end of input",
                tokens=self.tokens,
                position=self.current,
            )

        if token.type == TokenType.LEFT_PAREN:
            return self._parse_list()
        elif token.type == TokenType.QUOTE:
            return QuotedExpr(self.parse_expression())
        elif token.type == TokenType.SYMBOL:
            return SymbolExpr(token.value)
        elif token.type == TokenType.NUMBER:
            return NumberExpr(
                float(token.value) if "." in token.value else int(token.value)
            )
        elif token.type == TokenType.STRING:
            # Remove quotes and handle escape sequences
            return StringExpr(token.value[1:-1].replace('\\"', '"'))
        else:
            raise ElispParseError(
                message=f"Unexpected token: {token}",
                tokens=self.tokens,
                position=self.current,
            )

    def _parse_list(self) -> Expression:
        """Parse a list expression."""
        elements: List[Expression] = []

        while True:
            token = self.peek()

            if token is None:
                raise ElispParseError(
                    message="Unclosed list", tokens=self.tokens, position=self.current
                )

            if token.type == TokenType.RIGHT_PAREN:
                self.advance()
                return ListExpr(elements)

            if token.type == TokenType.DOT:
                self.advance()
                # Handle dotted pair (improper list)
                if len(elements) != 1:
                    raise ElispParseError(
                        message="Invalid dotted pair",
                        tokens=self.tokens,
                        position=self.current,
                    )
                cdr = self.parse_expression()
                token = self.peek()
                if token is None or token.type != TokenType.RIGHT_PAREN:
                    raise ElispParseError(
                        message="Expected ) after dotted pair",
                        tokens=self.tokens,
                        position=self.current,
                    )
                self.advance()
                return DottedPairExpr(elements[0], cdr)

            elements.append(self.parse_expression())

    def parse_all(self) -> List[Expression]:
        """Parse all expressions from the token stream."""
        expressions = []
        while self.current < len(self.tokens):
            expressions.append(self.parse_expression())
        return expressions


def parse_elisp(source: str) -> List[Expression]:
    """
    Parse Elisp source code into expression objects.

    Args:
        source: The Elisp source code

    Returns:
        List of Expression objects
    """
    tokens = tokenize(source)
    parser = Parser(list(tokens))
    return parser.parse_all()


# Pretty printer utilities
def pretty_print(expr: Expression, indent: int = 0) -> str:
    """Pretty print an Elisp expression."""
    indent_str = "  " * indent

    if isinstance(expr, SymbolExpr):
        return f"{indent_str}{expr.value}"

    elif isinstance(expr, NumberExpr):
        return f"{indent_str}{expr.value}"

    elif isinstance(expr, StringExpr):
        return f'{indent_str}"{expr.value}"'

    elif isinstance(expr, QuotedExpr):
        return f"{indent_str}'{pretty_print(expr.expression, 0)}"

    elif isinstance(expr, ListExpr):
        if not expr.elements:
            return f"{indent_str}()"

        result = [f"{indent_str}("]
        for i, element in enumerate(expr.elements):
            if i == 0:
                result.append(pretty_print(element, 0))
            else:
                result.append(pretty_print(element, indent + 1))
        result.append(f"{indent_str})")
        return "\n".join(result)

    elif isinstance(expr, DottedPairExpr):
        car_str = pretty_print(expr.car, 0)
        cdr_str = pretty_print(expr.cdr, 0)
        return f"{indent_str}({car_str} . {cdr_str})"

    else:
        return f"{indent_str}<unknown>"
