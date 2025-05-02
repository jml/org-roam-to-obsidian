import logging
import tomllib  # Standard library in Python 3.11+
from pathlib import Path
from typing import Any

from pydantic import ValidationError, field_validator
from pydantic.dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for the conversion process."""

    preserve_creation_date: bool = True
    frontmatter_format: str = "yaml"
    convert_tags: bool = True
    link_format: str = "[[${filename}]]"

    @field_validator("frontmatter_format")
    @classmethod
    def validate_frontmatter_format(cls, v: str) -> str:
        valid_formats = ["yaml", "json"]
        if v not in valid_formats:
            raise ValueError(f"Frontmatter format must be one of {valid_formats}")
        return v

    @field_validator("link_format")
    @classmethod
    def validate_link_format(cls, v: str) -> str:
        if "${filename}" not in v:
            raise ValueError("Link format must contain ${filename} placeholder")
        return v


@dataclass(frozen=True)
class AttachmentsConfig:
    """Configuration for handling attachments."""

    copy_attachments: bool = True
    attachment_folder: str = "assets"

    @field_validator("attachment_folder")
    @classmethod
    def validate_attachment_folder(cls, v: str) -> str:
        if "/" in v or "\\" in v:
            raise ValueError("Attachment folder cannot contain path separators")
        if not v:
            raise ValueError("Attachment folder cannot be empty")
        return v


@dataclass(frozen=True)
class FormattingConfig:
    """Configuration for text formatting."""

    convert_tables: bool = True
    convert_code_blocks: bool = True
    convert_latex: bool = True


@dataclass(frozen=True)
class ConverterConfig:
    """Complete configuration for the converter."""

    conversion: ConversionConfig
    attachments: AttachmentsConfig
    formatting: FormattingConfig

    def __post_init__(self) -> None:
        """Initialize default values if needed."""
        # With Pydantic dataclasses, values should never be None if they have defaults

    @classmethod
    def from_dict(cls, config_dict: dict[str, dict[str, Any]]) -> "ConverterConfig":
        """Create a config object from a dictionary."""
        try:
            conversion_dict = config_dict.get("conversion", {})
            attachments_dict = config_dict.get("attachments", {})
            formatting_dict = config_dict.get("formatting", {})

            conversion_config = ConversionConfig(**conversion_dict)
            attachments_config = AttachmentsConfig(**attachments_dict)
            formatting_config = FormattingConfig(**formatting_dict)

            return cls(
                conversion=conversion_config,
                attachments=attachments_config,
                formatting=formatting_config,
            )
        except ValidationError as e:
            log.error(f"Configuration validation error: {e}")
            # Re-raise to allow caller to handle
            raise
        except Exception as e:
            log.error(f"Error creating configuration: {e}")
            # Fall back to defaults
            return cls(
                conversion=ConversionConfig(),
                attachments=AttachmentsConfig(),
                formatting=FormattingConfig(),
            )

    @classmethod
    def from_file(cls, config_path: Path) -> "ConverterConfig":
        """Load configuration from a TOML file."""
        if not config_path.exists():
            log.warning(f"Config file not found: {config_path}, using defaults")
            return cls(
                conversion=ConversionConfig(),
                attachments=AttachmentsConfig(),
                formatting=FormattingConfig(),
            )

        try:
            # tomllib requires binary mode
            with open(config_path, "rb") as f:
                config_dict = tomllib.load(f)

            if not config_dict or not isinstance(config_dict, dict):
                log.warning(f"Invalid configuration in {config_path}, using defaults")
                return cls(
                    conversion=ConversionConfig(),
                    attachments=AttachmentsConfig(),
                    formatting=FormattingConfig(),
                )

            log.info(f"Loaded configuration from {config_path}")
            return cls.from_dict(config_dict)
        except ValidationError as e:
            log.error(f"Configuration validation error: {e}")
            # Re-raise to allow caller to handle
            raise
        except Exception as e:
            log.error(f"Error loading config file: {e}")
            return cls(
                conversion=ConversionConfig(),
                attachments=AttachmentsConfig(),
                formatting=FormattingConfig(),
            )


@dataclass(frozen=True)
class OrgRoamConverter:
    """Converts Org-roam files to Obsidian markdown format."""

    source: Path
    destination: Path
    config: ConverterConfig
    dry_run: bool = False

    def __post_init__(self) -> None:
        """Validation and setup after initialization."""
        if not self.source.exists():
            raise FileNotFoundError(f"Source database not found: {self.source}")

        if not self.dry_run:
            # We can't modify self.destination as it's frozen,
            # but we can create the directory if needed
            self.destination.mkdir(parents=True, exist_ok=True)

        # With Pydantic dataclasses, validation happens at initialization

    @classmethod
    def from_paths(
        cls,
        source: Path,
        destination: Path,
        config_path: Path | None = None,
        dry_run: bool = False,
    ) -> "OrgRoamConverter":
        """Create a converter from paths, loading configuration if provided."""
        # Create default config
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        # Load config from file if provided
        if config_path is not None:
            try:
                config = ConverterConfig.from_file(config_path)
            except ValidationError as e:
                # Log detailed validation errors
                log.error("Configuration validation errors:")
                for error in e.errors():
                    error_loc = " -> ".join(str(loc) for loc in error["loc"])
                    log.error(f"  - {error_loc}: {error['msg']}")
                # Re-raise to allow caller to handle
                raise

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
