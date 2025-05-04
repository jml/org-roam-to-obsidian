#!/usr/bin/env python3
"""
CLI for converting Org-roam files to Obsidian markdown.

This module serves as the entry point for the command-line interface.
It handles command-line arguments, initializes logging, and executes
the conversion process.

The module uses structlog for structured logging, which provides machine-readable
logs in JSON format by default, or human-friendly colored output in verbose mode.
To use structured logging in your own code:

1. Import the logger: `from org_roam_to_obsidian.logging import get_logger`
2. Create a logger: `log = get_logger(__name__)`
3. Log using key-value pairs: `log.info("event_name", key1="value1", key2="value2")`
"""

import sys
from pathlib import Path

import click
from pydantic import ValidationError

from org_roam_to_obsidian.converter import OrgRoamConverter
from org_roam_to_obsidian.logging import get_logger, setup_logging

log = get_logger(__name__)


@click.command()
@click.option(
    "--source",
    "-s",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to your org-roam database file",
)
@click.option(
    "--destination",
    "-d",
    required=True,
    type=click.Path(path_type=Path),
    help="Path for the new Obsidian vault",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to a TOML config file (optional)",
)
@click.option(
    "--source-base-path",
    "-b",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    help="Base path of org-roam files for preserving directory structure (optional)",
)
@click.option(
    "--dry-run", is_flag=True, help="Test the conversion without writing files"
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed conversion information"
)
def main(
    source: Path,
    destination: Path,
    config: Path | None,
    source_base_path: Path | None,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Convert Org-roam files to Obsidian markdown."""
    setup_logging(verbose)

    try:
        try:
            converter = OrgRoamConverter.from_paths(
                source=source,
                destination=destination,
                config_path=config,
                source_base_path=source_base_path,
                dry_run=dry_run,
            )
        except ValidationError as e:
            # Handle validation errors separately for better user experience
            log.error("configuration_validation_failed")
            for error in e.errors():
                error_path = " -> ".join(str(loc) for loc in error["loc"])
                log.error("validation_error", path=error_path, message=error["msg"])
            click.echo("Please fix the configuration errors and try again.", err=True)
            return 1

        converter.run()
        return 0

    except Exception as e:
        log.error("conversion_failed", error=str(e))
        if verbose:
            log.exception("detailed_error_information")
        return 1


if __name__ == "__main__":
    sys.exit(main())
