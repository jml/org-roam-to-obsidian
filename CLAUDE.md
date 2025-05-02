# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Core Development Rules

1. Package Management
   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax

2. Code Quality
   - Type hints required for all code
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 88 chars maximum

3. Testing Requirements
   - Framework: `uv run --frozen pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests
   - Test docstrings:
     - Focus on behavior being tested, not implementation
     - Remove redundant phrases like "Test that..." or "Check that..."
     - Omit words like "correctly," "properly," or "as expected"
     - Explain why the test matters when it's not obvious
     - When possible, provide context about the test's significance
     - Keep concise but informative - choose clarity over brevity

4.  Error Handling
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
   - Tool: `uv run --frozen mypy`
   - Requirements:
     - Explicit None checks for Optional
     - Type narrowing for strings
     - Version warnings can be ignored if checks pass
     - `Type | None` syntax for optional types

## Error Resolution

1. CI Failures
   - Fix order:
     1. Formatting
     2. Type errors
     3. Linting
   - Type errors:
     - Get full line context
     - Check Optional types
     - Add type narrowing
     - Verify function signatures

2. Common Issues
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports
   - Types:
     - Add None checks
     - Narrow string types
     - Match existing patterns

3. Best Practices
   - Check git status before commits
   - Run formatters before type checks
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs
   - Test thoroughly
