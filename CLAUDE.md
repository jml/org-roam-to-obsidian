# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Core Development Rules

### Package Management

   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax
   - Use `uv run pip` instead of `pip`

### Code Quality

   - Type hints required for all code
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 88 chars maximum

### Testing Requirements

   - Framework: `uv run --frozen pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests
   - Never use mocks
   - When comparing dataclass values for equality in tests, assert on the whole object, rather than on individual attributes

#### Test docstrings
     - Focus on behavior being tested, not implementation
     - Remove redundant phrases like "Test that..." or "Check that..."
     - Omit words like "correctly," "properly," or "as expected"
     - Explain why the test matters when it's not obvious
     - When possible, provide context about the test's significance
     - Keep concise but informative - choose clarity over brevity

###  Error Handling
  - Use specific exception types and descriptive error messages
  - Never catch an exception just to log it and re-raise; let it propagate naturally
  - Handle exceptions only where you can take meaningful action
  - Provide reasonable fallbacks for recoverable errors
  - Log errors with enough context to diagnose the issue

## Python Idioms

-  **Version**: Use Python 3.11+
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Classes**: Use frozen dataclasses (`@dataclass(frozen=True)`) for data-oriented classes
- **Type Annotations**: Use list, dict, etc. for types rather than importing List, Dict, etc from typing
- **Optional Types**: Use `Type | None` syntax rather than `Optional[Type]` for optional values

## File layout

- Code lives in a `src` directory, and tests live in a separate top-level `tests` directory

## Code Formatting

1. Ruff
   - Format: `uv run --frozen ruff format .`
   - Check: `uv run --frozen ruff check .`
   - Fix: `uv run --frozen ruff check . --fix`
   - Critical issues:
     - Line length (88 chars)
     - Import sorting (I001)
     - Unused imports
   - Line wrapping:
     - Strings: use parentheses
     - Function calls: multi-line with proper indent
     - Imports: split into multiple lines

2. Type Checking
   - Tool: `uv run --frozen mypy src tests`
   - Requirements:
     - Explicit None checks for Optional
     - Type narrowing for strings
     - Version warnings can be ignored if checks pass
     - `Type | None` syntax for optional types