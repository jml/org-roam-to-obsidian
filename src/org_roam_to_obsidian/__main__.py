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
    "--source-base-path",
    "-b",
    required=True,
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    help="Base path of org-roam files for preserving directory structure",
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
    source_base_path: Path | None,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Convert Org-roam files to Obsidian markdown."""
    setup_logging(verbose)

    try:
        # If source_base_path is not provided, use parent of source database
        base_path = source_base_path if source_base_path is not None else source.parent
        converter = OrgRoamConverter(
            source=source,
            destination=destination,
            source_base_path=base_path,
            dry_run=dry_run,
        )
        converter.run()
        return 0

    except Exception as e:
        log.error("conversion_failed", error=str(e))
        if verbose:
            log.exception("detailed_error_information")
        return 1


if __name__ == "__main__":
    sys.exit(main())
