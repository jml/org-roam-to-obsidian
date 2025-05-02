# Justfile for org-roam-to-obsidian

# List available commands
default:
    @just --list

# Install the package in development mode
install:
    uv pip install -e .

# Run all checks (format, lint, typecheck, test)
check: format lint typecheck test

# Run type checking with mypy
typecheck:
    uv run mypy src tests

# Format code with ruff
format:
    ruff format .

# Lint code with ruff
lint:
    ruff check .

# Run tests with pytest
test:
    pytest

# Run a specific test
test-one TEST:
    pytest {{TEST}} -v

# Run the application
run SOURCE DEST *ARGS:
    python -m org_roam_to_obsidian --source {{SOURCE}} --destination {{DEST}} {{ARGS}}

# Run with verbose output
run-verbose SOURCE DEST *ARGS:
    python -m org_roam_to_obsidian --source {{SOURCE}} --destination {{DEST}} --verbose {{ARGS}}

# Clean up build artifacts
clean:
    rm -rf build dist *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete