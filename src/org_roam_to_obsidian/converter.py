from pathlib import Path
import logging
import yaml
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


class OrgRoamConverter:
    """Converts Org-roam files to Obsidian markdown format."""

    DEFAULT_CONFIG = {
        "conversion": {
            "preserve_creation_date": True,
            "frontmatter_format": "yaml",
            "convert_tags": True,
            "link_format": "[[${filename}]]",
        },
        "attachments": {
            "copy_attachments": True,
            "attachment_folder": "assets",
        },
        "formatting": {
            "convert_tables": True,
            "convert_code_blocks": True,
            "convert_latex": True,
        },
    }

    def __init__(
        self,
        source: Path,
        destination: Path,
        config_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> None:
        """Initialize the converter with source, destination and configuration.

        Args:
            source: Path to the org-roam database file
            destination: Path for the new Obsidian vault
            config_path: Optional path to a config YAML file
            dry_run: If True, don't write any files, just simulate
        """
        self.source = source
        self.destination = destination
        self.dry_run = dry_run
        self.config = self._load_config(config_path)

        if not self.source.exists():
            raise FileNotFoundError(f"Source database not found: {self.source}")

        if not self.dry_run:
            self.destination.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        config = self.DEFAULT_CONFIG.copy()

        if config_path is not None:
            if not config_path.exists():
                log.warning(f"Config file not found: {config_path}, using defaults")
            else:
                try:
                    with open(config_path, "r") as f:
                        user_config = yaml.safe_load(f)

                    # Merge user config with defaults
                    if user_config and isinstance(user_config, dict):
                        self._merge_configs(config, user_config)
                        log.info(f"Loaded configuration from {config_path}")
                except Exception as e:
                    log.error(f"Error loading config file: {e}")

        return config

    def _merge_configs(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """Recursively merge overlay dictionary into base dictionary."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def run(self) -> None:
        """Run the conversion process."""
        log.info(f"Starting conversion from {self.source} to {self.destination}")
        log.info("Dry run mode" if self.dry_run else "Live conversion mode")

        # TODO: Implement conversion logic
        # 1. Read org-roam database
        # 2. Process each org file
        # 3. Write converted markdown to destination

        log.info("Conversion complete")
