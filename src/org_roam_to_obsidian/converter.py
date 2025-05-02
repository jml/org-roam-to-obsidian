import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for the conversion process."""

    preserve_creation_date: bool = True
    frontmatter_format: str = "yaml"
    convert_tags: bool = True
    link_format: str = "[[${filename}]]"


@dataclass(frozen=True)
class AttachmentsConfig:
    """Configuration for handling attachments."""

    copy_attachments: bool = True
    attachment_folder: str = "assets"


@dataclass(frozen=True)
class FormattingConfig:
    """Configuration for text formatting."""

    convert_tables: bool = True
    convert_code_blocks: bool = True
    convert_latex: bool = True


@dataclass(frozen=True)
class ConverterConfig:
    """Complete configuration for the converter."""

    conversion: ConversionConfig = field(default_factory=ConversionConfig)
    attachments: AttachmentsConfig = field(default_factory=AttachmentsConfig)
    formatting: FormattingConfig = field(default_factory=FormattingConfig)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "ConverterConfig":
        """Create a config object from a dictionary."""
        conversion_config = ConversionConfig(**config_dict.get("conversion", {}))
        attachments_config = AttachmentsConfig(**config_dict.get("attachments", {}))
        formatting_config = FormattingConfig(**config_dict.get("formatting", {}))

        return cls(
            conversion=conversion_config,
            attachments=attachments_config,
            formatting=formatting_config,
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "ConverterConfig":
        """Load configuration from a YAML file."""
        if not config_path.exists():
            log.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)

            if not config_dict or not isinstance(config_dict, dict):
                log.warning(f"Invalid configuration in {config_path}, using defaults")
                return cls()

            log.info(f"Loaded configuration from {config_path}")
            return cls.from_dict(config_dict)
        except Exception as e:
            log.error(f"Error loading config file: {e}")
            return cls()


@dataclass(frozen=True)
class OrgRoamConverter:
    """Converts Org-roam files to Obsidian markdown format."""

    source: Path
    destination: Path
    config: ConverterConfig = field(default_factory=ConverterConfig)
    dry_run: bool = False

    def __post_init__(self) -> None:
        """Validation and setup after initialization."""
        if not self.source.exists():
            raise FileNotFoundError(f"Source database not found: {self.source}")

        if not self.dry_run:
            # We can't modify self.destination as it's frozen,
            # but we can create the directory if needed
            self.destination.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_paths(
        cls,
        source: Path,
        destination: Path,
        config_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> "OrgRoamConverter":
        """Create a converter from paths, loading configuration if provided."""
        config = ConverterConfig()
        if config_path is not None:
            config = ConverterConfig.from_file(config_path)

        return cls(
            source=source,
            destination=destination,
            config=config,
            dry_run=dry_run,
        )

    def run(self) -> None:
        """Run the conversion process."""
        log.info(f"Starting conversion from {self.source} to {self.destination}")
        log.info("Dry run mode" if self.dry_run else "Live conversion mode")

        # TODO: Implement conversion logic
        # 1. Read org-roam database
        # 2. Process each org file
        # 3. Write converted markdown to destination

        log.info("Conversion complete")
