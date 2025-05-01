# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- Install dependencies: `uv pip install -e .`
- Run: `python -m org_roam_to_obsidian --source <path> --destination <path>`
- Lint: `ruff check .`
- Format: `ruff format .`
- Test: `pytest`
- Single test: `pytest tests/test_file.py::test_function -v`

## Code Style Guidelines
- **Python Version**: 3.11+
- **Package Manager**: uv
- **Formatting**: ruff format with 88 character line length (Black style)
- **Linting**: ruff with isort for import sorting
- **Imports**: Group imports (standard library, third-party, local) with blank lines between groups
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Type Hints**: Use type annotations for function parameters and return values
- **Error Handling**: Use specific exception types and descriptive error messages
- **Testing**: pytest with fixtures and parametrized tests when appropriate
- **Whitespace**: Avoid trailing whitespace

## Architecture Notes
- CLI tool for converting Org-roam files to Obsidian Markdown
- Focus on preserving links, metadata, and maintaining note integrity
- Configure via command-line options and config.yml file
- Code lives in a `src` directory, and tests live in a separate top-level `tests` directory