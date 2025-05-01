#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path

from org_roam_to_obsidian.converter import OrgRoamConverter

log = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Org-roam files to Obsidian markdown"
    )
    
    parser.add_argument(
        "--source", "-s", 
        required=True,
        type=Path, 
        help="Path to your org-roam database file"
    )
    
    parser.add_argument(
        "--destination", "-d",
        required=True, 
        type=Path,
        help="Path for the new Obsidian vault"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to a config file (optional)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test the conversion without writing files"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed conversion information"
    )
    
    return parser.parse_args()


def main() -> int:
    """Run the converter application."""
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        converter = OrgRoamConverter(
            source=args.source,
            destination=args.destination,
            config_path=args.config,
            dry_run=args.dry_run,
        )
        
        converter.run()
        return 0
    
    except Exception as e:
        log.error(f"Error: {e}")
        if args.verbose:
            log.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
