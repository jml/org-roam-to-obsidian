import tomllib  # Standard library in Python 3.11+
from pathlib import Path

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from org_roam_to_obsidian.logging import get_logger

log = get_logger(__name__)


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

    # The constructor can handle nested dictionaries directly

    @classmethod
    def from_file(cls, config_path: Path) -> "ConverterConfig":
        """Load configuration from a TOML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # tomllib requires binary mode
        with open(config_path, "rb") as f:
            config_dict = tomllib.load(f)

        if not config_dict or not isinstance(config_dict, dict):
            raise ValueError(f"Invalid configuration format in {config_path}")

        log.info("loaded_configuration", config_path=str(config_path))
        # ValidationError from Pydantic will propagate to caller
        # We can directly pass the dictionary to the constructor
        return cls(**config_dict)


DEFAULT_CONFIG = ConverterConfig(
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
        config = DEFAULT_CONFIG

        # Load config from file if provided
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
        log.info(
            "starting_conversion",
            source=str(self.source),
            destination=str(self.destination),
            dry_run=self.dry_run,
        )

        # TODO: Implement conversion logic
        # 1. Read org-roam database
        # 2. Process each org file
        # 3. Write converted markdown to destination

        log.info("conversion_complete")
