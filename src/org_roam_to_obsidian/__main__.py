#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

import click
from pydantic import ValidationError

from org_roam_to_obsidian.converter import OrgRoamConverter

log = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


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
    "--dry-run", is_flag=True, help="Test the conversion without writing files"
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed conversion information"
)
def main(
    source: Path, destination: Path, config: Path | None, dry_run: bool, verbose: bool
) -> int:
    """Convert Org-roam files to Obsidian markdown."""
    setup_logging(verbose)

    try:
        try:
            converter = OrgRoamConverter.from_paths(
                source=source,
                destination=destination,
                config_path=config,
                dry_run=dry_run,
            )
        except ValidationError as e:
            # Handle validation errors separately for better user experience
            log.error("Configuration validation failed:")
            for error in e.errors():
                error_path = " -> ".join(str(loc) for loc in error["loc"])
                log.error(f"  - {error_path}: {error['msg']}")
            click.echo("Please fix the configuration errors and try again.", err=True)
            return 1

        converter.run()
        return 0

    except Exception as e:
        log.error(f"Error: {e}")
        if verbose:
            log.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
