import json
import tomllib  # Standard library in Python 3.11+
from pathlib import Path
from typing import Any, cast

import pypandoc  # type: ignore
import yaml
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from org_roam_to_obsidian.database import OrgRoamDatabase, OrgRoamFile, OrgRoamNode
from org_roam_to_obsidian.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for the conversion process."""

    frontmatter_format: str = "yaml"
    convert_tags: bool = True
    link_format: str = "[[${filename}]]"
    preserve_path_structure: bool = True

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
    source_base_path: Path
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
        source_base_path: Path,
        config_path: Path | None = None,
        dry_run: bool = False,
    ) -> "OrgRoamConverter":
        """Create a converter from paths, loading configuration if provided."""
        config = DEFAULT_CONFIG

        # Load config from file if provided
        if config_path is not None:
            config = ConverterConfig.from_file(config_path)

        log.info("source_base_path_set", path=str(source_base_path))

        return cls(
            source=source,
            destination=destination,
            config=config,
            source_base_path=source_base_path,
            dry_run=dry_run,
        )

    def _convert_file(self, src_file: Path) -> str:
        """
        Convert an org file to markdown format using pypandoc.

        Args:
            src_file: Path to the source org file

        Returns:
            Converted markdown content as a string
        """
        # Check if the source file exists
        if not src_file.exists():
            log.warning("source_file_not_found", file=str(src_file))
            return ""

        # Use pypandoc to convert from org to markdown
        # 'gfm' is GitHub-flavored Markdown which is close to Obsidian markdown
        markdown_content = pypandoc.convert_file(
            src_file,
            "gfm",  # GitHub-flavored Markdown
            format="org",
        )

        log.info("converted_file", source=str(src_file))
        return cast(str, markdown_content)

    def _get_destination_path(self, src_file: Path) -> Path:
        """
        Determine the destination path for a converted markdown file.

        Preserves the directory structure from the source based on configuration,
        and changes the extension to .md

        Args:
            src_file: Path to the source org file

        Returns:
            Path to the destination markdown file
        """
        # Change extension to .md
        dest_filename = src_file.stem + ".md"

        if self.config.conversion.preserve_path_structure:
            # Get the base path for calculating relative paths
            base_path = self.source_base_path

            # Try to resolve both paths to absolute paths to handle symlinks
            try:
                abs_src_file = src_file.resolve()
                abs_base_path = base_path.resolve()

                # Check if the source file exists
                if not abs_src_file.exists():
                    log.warning(
                        "source_file_does_not_exist",
                        file=str(src_file),
                        resolved=str(abs_src_file),
                    )
                    # Fall back to the original path for calculation
                    abs_src_file = src_file

                # Calculate the relative path from the base directory
                try:
                    # First try with resolved paths
                    rel_path = abs_src_file.relative_to(abs_base_path)
                    log.debug(
                        "using_resolved_paths",
                        src_file=str(abs_src_file),
                        base_path=str(abs_base_path),
                        rel_path=str(rel_path),
                    )
                except ValueError:
                    # If that fails, try with the original paths
                    log.debug("resolved_paths_not_relative", trying_original_paths=True)
                    rel_path = src_file.relative_to(base_path)
                    log.debug(
                        "using_original_paths",
                        src_file=str(src_file),
                        base_path=str(base_path),
                        rel_path=str(rel_path),
                    )

                # If it's just a filename (no directory), use it directly
                if len(rel_path.parts) > 1:
                    # Get the directory part (exclude filename)
                    rel_dir = rel_path.parent

                    # Construct the destination path with preserved structure
                    dest_path = self.destination / rel_dir / dest_filename

                    log.debug(
                        "preserving_directory_structure",
                        rel_dir=str(rel_dir),
                        dest_path=str(dest_path),
                    )
                else:
                    # No directory structure to preserve
                    dest_path = self.destination / dest_filename

                    log.debug(
                        "no_directory_structure_to_preserve", dest_path=str(dest_path)
                    )

            except ValueError as e:
                # If the file is not relative to the base path,
                # fall back to just using the filename
                log.warning(
                    "file_not_relative_to_base_path",
                    file=str(src_file),
                    base_path=str(base_path),
                    error=str(e),
                )
                dest_path = self.destination / dest_filename
        else:
            # Simple approach: just use the filename without preserving structure
            dest_path = self.destination / dest_filename

        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        return dest_path

    def _process_files(
        self, files: list[OrgRoamFile], file_to_nodes: dict[Path, list[OrgRoamNode]]
    ) -> None:
        """
        Process all org files and convert them to markdown with frontmatter.

        Args:
            files: List of OrgRoamFile objects to process
            file_to_nodes: Mapping from file paths to their associated nodes
        """
        # For each file in the database
        for org_file in files:
            try:
                # Get source file path
                src_file = Path(org_file.file_path)

                # Get destination path for the markdown file
                dest_file = self._get_destination_path(src_file)

                # Skip if dry run
                if self.dry_run:
                    log.info(
                        "dry_run_would_convert",
                        source=str(src_file),
                        dest=str(dest_file),
                    )
                    continue

                # Convert org to markdown
                markdown_content = self._convert_file(src_file)

                # Get primary node for this file (first node in file, if any)
                primary_node = None
                if src_file in file_to_nodes and file_to_nodes[src_file]:
                    primary_node = file_to_nodes[src_file][0]

                # Only generate frontmatter if we have a node
                if primary_node:
                    # Generate frontmatter data and format it
                    frontmatter_data = self._generate_frontmatter_data(
                        primary_node, self.config.conversion
                    )
                    frontmatter = self._format_frontmatter(
                        frontmatter_data, self.config.conversion.frontmatter_format
                    )

                    # Combine frontmatter and content
                    final_content = frontmatter + markdown_content
                else:
                    # No node found, skip frontmatter
                    final_content = markdown_content
                    log.info(
                        "skipping_frontmatter",
                        source=str(src_file),
                        reason="no_node_found",
                    )

                # Write to destination
                with open(dest_file, "w") as f:
                    f.write(final_content)

                log.info(
                    "file_converted",
                    source=str(src_file),
                    dest=str(dest_file),
                    has_frontmatter=primary_node is not None,
                )

            except Exception as e:
                log.error(
                    "file_conversion_failed",
                    file=str(org_file.file_path),
                    error=str(e),
                )

    def _format_frontmatter(self, data: dict[str, Any], format_type: str) -> str:
        """
        Format frontmatter data as YAML or JSON.

        Args:
            data: Dictionary containing frontmatter data
            format_type: Format type ('yaml' or 'json')

        Returns:
            String containing the formatted frontmatter
        """
        if format_type == "yaml":
            frontmatter = "---\n"
            frontmatter += yaml.dump(data, sort_keys=False)
            frontmatter += "---\n\n"
        else:  # JSON format
            frontmatter = "---\n"
            frontmatter += json.dumps(data, indent=2)
            frontmatter += "\n---\n\n"

        return frontmatter

    def _generate_frontmatter_data(
        self, node: OrgRoamNode, config: ConversionConfig
    ) -> dict[str, object]:
        """
        Generate frontmatter data dictionary for a markdown file based on node metadata.

        Args:
            node: OrgRoamNode containing metadata
            config: Configuration for the frontmatter generation

        Returns:
            Dictionary containing the frontmatter data
        """
        # Extract metadata from node
        frontmatter_data: dict[str, object] = {
            "title": node.title,
        }

        # Add aliases if available
        if node.aliases:
            frontmatter_data["aliases"] = node.aliases

        # Add tags if configured and available
        if config.convert_tags and node.tags:
            frontmatter_data["tags"] = node.tags

        return frontmatter_data

    def run(self) -> None:
        """Run the conversion process."""
        log.info(
            "starting_conversion",
            source=str(self.source),
            destination=str(self.destination),
            dry_run=self.dry_run,
        )

        # Open the org-roam database
        with OrgRoamDatabase(self.source) as db:
            # Get all files tracked by org-roam
            log.info("reading_files")
            files = list(db.get_all_files())
            log.info("files_read", count=len(files))

            # Get all nodes from the database
            log.info("reading_nodes")
            nodes = list(db.get_all_nodes())
            log.info("nodes_read", count=len(nodes))

            # Create ID to filename map for link conversion
            log.info("creating_id_map")
            id_to_file = db.create_id_to_filename_map()
            log.info("id_map_created", count=len(id_to_file))

            # Create file to nodes map for frontmatter generation
            log.info("creating_file_to_nodes_map")
            file_to_nodes = db.create_file_to_nodes_map()
            log.info("file_to_nodes_map_created", count=len(file_to_nodes))

            # Process and convert all files
            log.info("processing_files")
            self._process_files(files, file_to_nodes)
            log.info("files_processed", count=len(files))

        log.info("conversion_complete")
