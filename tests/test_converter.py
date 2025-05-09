import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from org_roam_to_obsidian.converter import (
    DEFAULT_CONFIG,
    AttachmentsConfig,
    ConversionConfig,
    ConverterConfig,
    FormattingConfig,
    OrgRoamConverter,
)


@pytest.fixture
def temp_source():
    """Create a temporary file to use as source."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        path = Path(f.name)
        yield path


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        yield path


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary TOML config file."""
    config_content = """
[conversion]
frontmatter_format = "yaml"
convert_tags = true
link_format = "[[${title}]]"
preserve_path_structure = true
preserve_link_descriptions = true
link_description_format = "[[${title}|${description}]]"

[attachments]
copy_attachments = true
attachment_folder = "custom_assets"

[formatting]
convert_tables = true
convert_code_blocks = false
convert_latex = true
"""
    config_path = temp_dir / "config.toml"
    with open(config_path, "w") as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def temp_config_with_base_path(temp_dir, nested_org_files):
    """Create a temporary TOML config file."""
    config_content = """
[conversion]
frontmatter_format = "yaml"
convert_tags = true
link_format = "[[${title}]]"
preserve_path_structure = true
preserve_link_descriptions = true
link_description_format = "[[${title}|${description}]]"

[attachments]
copy_attachments = true
attachment_folder = "custom_assets"

[formatting]
convert_tables = true
convert_code_blocks = false
convert_latex = true
"""
    config_path = temp_dir / "config_with_base.toml"
    with open(config_path, "w") as f:
        f.write(config_content)
    return config_path


class TestConfigClasses:
    """Test the configuration dataclasses."""

    def test_conversion_config_defaults(self):
        """Default initialization of ConversionConfig sets expected values."""
        config = ConversionConfig()
        expected = ConversionConfig(
            frontmatter_format="yaml",
            convert_tags=True,
            link_format="[[${title}]]",
            preserve_path_structure=True,
            preserve_link_descriptions=True,
            link_description_format="[[${title}|${description}]]",
        )
        assert config == expected

    def test_conversion_config_validation(self):
        """ConversionConfig validation prevents invalid format and link configs."""
        # Valid format
        config = ConversionConfig(frontmatter_format="json")
        assert config.frontmatter_format == "json"

        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            ConversionConfig(frontmatter_format="invalid")
        error_msg = str(exc_info.value)
        assert "Frontmatter format must be one of" in error_msg

        # Invalid link format
        with pytest.raises(ValidationError) as exc_info:
            ConversionConfig(link_format="[[no-placeholder]]")
        error_msg = str(exc_info.value)
        assert "Link format must contain ${title} placeholder" in error_msg

        # Invalid link description format
        with pytest.raises(ValidationError) as exc_info:
            ConversionConfig(link_description_format="[[missing-placeholders]]")
        error_msg = str(exc_info.value)
        assert (
            "Link description format must contain both ${title} and ${description} placeholders"
            in error_msg
        )

    def test_attachments_config_defaults(self):
        """AttachmentsConfig initializes with default folder name and copy behavior."""
        config = AttachmentsConfig()
        expected = AttachmentsConfig(
            copy_attachments=True,
            attachment_folder="assets",
        )
        assert config == expected

    def test_attachments_config_validation(self):
        """AttachmentsConfig rejects folders with path separators or empty names."""
        # Valid custom folder
        config = AttachmentsConfig(attachment_folder="images")
        assert config.attachment_folder == "images"

        # Invalid folder with path separator
        with pytest.raises(ValidationError) as exc_info:
            AttachmentsConfig(attachment_folder="invalid/path")
        error_msg = str(exc_info.value)
        assert "Attachment folder cannot contain path separators" in error_msg

        # Empty folder
        with pytest.raises(ValidationError) as exc_info:
            AttachmentsConfig(attachment_folder="")
        error_msg = str(exc_info.value)
        assert "Attachment folder cannot be empty" in error_msg

    def test_formatting_config_defaults(self):
        """FormattingConfig enables all content conversion options by default."""
        config = FormattingConfig()
        expected = FormattingConfig(
            convert_tables=True,
            convert_code_blocks=True,
            convert_latex=True,
        )
        assert config == expected

    def test_converter_config_defaults(self):
        """ConverterConfig correctly composes nested configuration objects."""
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )
        expected = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )
        assert config == expected


class TestOrgRoamConverter:
    """Test the OrgRoamConverter class."""

    @pytest.fixture
    def nested_org_files(self, temp_dir):
        """Create a nested directory structure with org files for testing."""
        # Create main directory
        org_root = temp_dir / "org_files"
        org_root.mkdir(exist_ok=True)

        # Create nested directories
        nested_dir1 = org_root / "dir1"
        nested_dir1.mkdir(exist_ok=True)

        nested_dir2 = org_root / "dir1" / "dir2"
        nested_dir2.mkdir(exist_ok=True)

        # Create some org files in different directories
        root_file = org_root / "root.org"
        dir1_file = nested_dir1 / "file1.org"
        dir2_file = nested_dir2 / "file2.org"

        # Write some content to the files
        for file_path in [root_file, dir1_file, dir2_file]:
            with open(file_path, "w") as f:
                f.write(f"* Test content for {file_path.name}\n")

        return {
            "base_path": org_root,
            "files": [root_file, dir1_file, dir2_file],
        }

    def test_get_destination_path_with_path_structure(
        self, temp_source, temp_dir, nested_org_files
    ):
        """Test preserving directory structure in destination paths."""
        # Tests directory structure preservation
        # Create converter with path preservation enabled and specified base path
        config = ConverterConfig(
            conversion=ConversionConfig(
                preserve_path_structure=True,
            ),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        output_dir = temp_dir / "output"
        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
            config=config,
            source_base_path=nested_org_files["base_path"],
        )

        # Test with OrgRoamNode objects
        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test nodes with titles different from filenames
        root_node = OrgRoamNode(
            id="root-id",
            file_path=nested_org_files["files"][0],  # root.org
            title="Root Node Title",
            level=1,
            pos=0,
        )
        dir1_node = OrgRoamNode(
            id="dir1-id",
            file_path=nested_org_files["files"][1],  # dir1/file1.org
            title="Dir1 Node Title",
            level=1,
            pos=0,
        )
        dir2_node = OrgRoamNode(
            id="dir2-id",
            file_path=nested_org_files["files"][2],  # dir1/dir2/file2.org
            title="Dir2 Node Title",
            level=1,
            pos=0,
        )

        # Check that paths are preserved correctly with node titles
        root_dest = converter._get_destination_path(root_node)
        dir1_dest = converter._get_destination_path(dir1_node)
        dir2_dest = converter._get_destination_path(dir2_node)

        # Verify destinations maintain the same structure but use node
        # title for filename
        assert root_dest == output_dir / "Root Node Title.md"
        assert dir1_dest == output_dir / "dir1" / "Dir1 Node Title.md"
        assert dir2_dest == output_dir / "dir1" / "dir2" / "Dir2 Node Title.md"

        # Verify parent directories were created
        assert output_dir.exists()
        assert (output_dir / "dir1").exists()
        assert (output_dir / "dir1" / "dir2").exists()

    def test_get_destination_path_without_path_structure(
        self, temp_source, temp_dir, nested_org_files
    ):
        """Test flattening directory structure in destination paths."""
        # Tests directory structure flattening
        # Create converter with path preservation disabled
        config = ConverterConfig(
            conversion=ConversionConfig(
                preserve_path_structure=False,
            ),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        output_dir = temp_dir / "output_flat"
        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
            config=config,
            source_base_path=temp_source.parent,
        )

        # Test with OrgRoamNode objects
        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test nodes with titles different from filenames
        root_node = OrgRoamNode(
            id="root-id",
            file_path=nested_org_files["files"][0],  # root.org
            title="Root Node Title",
            level=1,
            pos=0,
        )
        dir1_node = OrgRoamNode(
            id="dir1-id",
            file_path=nested_org_files["files"][1],  # dir1/file1.org
            title="Dir1 Node Title",
            level=1,
            pos=0,
        )
        dir2_node = OrgRoamNode(
            id="dir2-id",
            file_path=nested_org_files["files"][2],  # dir1/dir2/file2.org
            title="Dir2 Node Title with / special chars",
            level=1,
            pos=0,
        )

        # Check that paths are flattened and use node titles
        root_dest = converter._get_destination_path(root_node)
        dir1_dest = converter._get_destination_path(dir1_node)
        dir2_dest = converter._get_destination_path(dir2_node)

        # Verify all files end up in the root output directory with node titles
        assert root_dest == output_dir / "Root Node Title.md"
        assert dir1_dest == output_dir / "Dir1 Node Title.md"
        assert dir2_dest == output_dir / "Dir2 Node Title with - special chars.md"

        # Verify parent directory was created
        assert output_dir.exists()

    def test_get_destination_path_handles_special_characters(
        self, temp_source, temp_dir
    ):
        """Test handling of special characters in node titles for filenames."""
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        output_dir = temp_dir / "output_special"
        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
            config=config,
            source_base_path=temp_source.parent,
        )

        # Create a test file
        test_file = temp_dir / "test.org"
        with open(test_file, "w") as f:
            f.write("* Test content\n")

        from org_roam_to_obsidian.database import OrgRoamNode

        # Test with various special characters in titles
        special_char_cases = [
            ("Title with / slashes", "Title with - slashes.md"),
            ("Title with \\ backslashes", "Title with - backslashes.md"),
            ("Title with both / and \\ slashes", "Title with both - and - slashes.md"),
            # In real code, quotes would have been parsed out by database.py
            ("Title with quotes", "Title with quotes.md"),
            ("Title with quotes in middle", "Title with quotes in middle.md"),
        ]

        for title, expected_filename in special_char_cases:
            node = OrgRoamNode(
                id="test-id",
                file_path=test_file,
                title=title,
                level=1,
                pos=0,
            )

            dest_path = converter._get_destination_path(node)
            assert dest_path.name == expected_filename

    def test_init(self, temp_source, temp_dir):
        """Converter initialization stores source, destination and configuration."""
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
            dry_run=True,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
            dry_run=True,
        )
        assert converter == expected

    def test_from_paths(self, temp_source, temp_dir):
        """Factory method creates converter from source and destination paths."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
            dry_run=True,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=DEFAULT_CONFIG,
            source_base_path=temp_source.parent,
            dry_run=True,
        )
        assert converter == expected

    def test_default_config(self, temp_source, temp_dir):
        """Default configuration sets expected values for all nested config objects."""
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
            dry_run=False,
        )
        assert converter == expected

    def test_from_toml_config(self, temp_source, temp_dir, temp_config_file):
        """Loading from TOML config file overrides default configuration values."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
            config_path=temp_config_file,
        )

        # Create the expected config with the values from the TOML file
        expected_config = ConverterConfig(
            conversion=ConversionConfig(
                frontmatter_format="yaml",
                convert_tags=True,
                link_format="[[${title}]]",
                preserve_path_structure=True,
                preserve_link_descriptions=True,
                link_description_format="[[${title}|${description}]]",
            ),
            attachments=AttachmentsConfig(
                copy_attachments=True,
                attachment_folder="custom_assets",
            ),
            formatting=FormattingConfig(
                convert_tables=True,
                convert_code_blocks=False,
                convert_latex=True,
            ),
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=expected_config,
            source_base_path=temp_source.parent,
            dry_run=False,
        )

        assert converter == expected

    def test_from_paths_with_source_base_path(
        self, temp_source, temp_dir, nested_org_files
    ):
        """Test that source_base_path is correctly set when provided to from_paths."""
        base_path = nested_org_files["base_path"]

        # Create converter with source_base_path
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            source_base_path=base_path,
        )

        # Verify source_base_path was set correctly
        assert converter.source_base_path == base_path

        # Test for each file in the nested structure
        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test nodes
        root_node = OrgRoamNode(
            id="root-id",
            file_path=nested_org_files["files"][0],  # root.org
            title="root",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )
        dir1_node = OrgRoamNode(
            id="dir1-id",
            file_path=nested_org_files["files"][1],  # dir1/file1.org
            title="file1",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )
        dir2_node = OrgRoamNode(
            id="dir2-id",
            file_path=nested_org_files["files"][2],  # dir1/dir2/file2.org
            title="file2",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )

        # Check that paths are preserved correctly using the provided base path
        root_dest = converter._get_destination_path(root_node)
        dir1_dest = converter._get_destination_path(dir1_node)
        dir2_dest = converter._get_destination_path(dir2_node)

        # Verify destinations maintain the same structure relative to base_path
        assert root_dest == temp_dir / "root.md"
        assert dir1_dest == temp_dir / "dir1" / "file1.md"
        assert dir2_dest == temp_dir / "dir1" / "dir2" / "file2.md"

    def test_config_file_with_base_path(
        self, temp_source, temp_dir, nested_org_files, temp_config_with_base_path
    ):
        """Test that source_base_path can be provided separately from config file."""
        base_path = nested_org_files["base_path"]

        # Create converter with config file and explicitly provided source_base_path
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            config_path=temp_config_with_base_path,
            source_base_path=base_path,
        )

        # Verify source_base_path was set correctly
        assert converter.source_base_path == base_path

        # Test for each file in the nested structure
        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test nodes
        root_node = OrgRoamNode(
            id="root-id",
            file_path=nested_org_files["files"][0],  # root.org
            title="root",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )
        dir1_node = OrgRoamNode(
            id="dir1-id",
            file_path=nested_org_files["files"][1],  # dir1/file1.org
            title="file1",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )
        dir2_node = OrgRoamNode(
            id="dir2-id",
            file_path=nested_org_files["files"][2],  # dir1/dir2/file2.org
            title="file2",  # Using same name as file for consistent assertions
            level=1,
            pos=0,
        )

        # Check that paths are preserved correctly using the provided base path
        root_dest = converter._get_destination_path(root_node)
        dir1_dest = converter._get_destination_path(dir1_node)
        dir2_dest = converter._get_destination_path(dir2_node)

        # Verify destinations maintain the same structure relative to base_path
        assert root_dest == temp_dir / "root.md"
        assert dir1_dest == temp_dir / "dir1" / "file1.md"
        assert dir2_dest == temp_dir / "dir1" / "dir2" / "file2.md"

    def test_source_base_path_precedence(
        self, temp_source, temp_dir, nested_org_files, temp_config_with_base_path
    ):
        """Test that CLI source_base_path takes precedence over config file."""
        base_path = nested_org_files["base_path"]

        # Create a different base path to override the one in config
        override_path = temp_dir / "override_base"
        override_path.mkdir(exist_ok=True)

        # Create converter with both config file and override source_base_path
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            config_path=temp_config_with_base_path,
            source_base_path=override_path,
        )

        # Verify override source_base_path was used instead of config file value
        assert converter.source_base_path == override_path
        assert converter.source_base_path != base_path

    def test_invalid_config_handling(self, temp_source, temp_dir):
        """Config validation fails fast with invalid frontmatter or paths."""
        # Create an invalid config file - invalid frontmatter format
        invalid_format_content = """
        [conversion]
        frontmatter_format = "invalid"
        """
        invalid_format_path = temp_dir / "invalid_format.toml"
        with open(invalid_format_path, "w") as f:
            f.write(invalid_format_content)

        # Should raise ValidationError for invalid frontmatter format
        with pytest.raises(ValidationError) as exc_info:
            OrgRoamConverter.from_paths(
                source=temp_source,
                destination=temp_dir,
                source_base_path=temp_source.parent,
                config_path=invalid_format_path,
            )
        error_msg = str(exc_info.value)
        assert "Frontmatter format must be one of" in error_msg

        # Create an invalid config file - invalid attachment folder
        invalid_path_content = """
        [attachments]
        attachment_folder = "invalid/path"
        """
        invalid_path_config = temp_dir / "invalid_path.toml"
        with open(invalid_path_config, "w") as f:
            f.write(invalid_path_content)

        # Should raise ValidationError for invalid attachment folder
        with pytest.raises(ValidationError) as exc_info:
            OrgRoamConverter.from_paths(
                source=temp_source,
                destination=temp_dir,
                source_base_path=temp_source.parent,
                config_path=invalid_path_config,
            )
        error_msg = str(exc_info.value)
        assert "Attachment folder cannot contain path separators" in error_msg

    def test_nonexistent_config_file(self, temp_source, temp_dir):
        """Loading from non-existent config file path raises appropriate error."""
        nonexistent_path = temp_dir / "nonexistent_config.toml"

        with pytest.raises(FileNotFoundError) as exc_info:
            OrgRoamConverter.from_paths(
                source=temp_source,
                destination=temp_dir,
                source_base_path=temp_source.parent,
                config_path=nonexistent_path,
            )
        error_msg = str(exc_info.value)
        assert "Config file not found" in error_msg

    def test_invalid_config_format(self, temp_source, temp_dir):
        """Empty config file is rejected with appropriate error message."""
        # Create an empty config file
        empty_config_path = temp_dir / "empty_config.toml"
        with open(empty_config_path, "w") as f:
            f.write("")

        with pytest.raises(ValueError) as exc_info:
            OrgRoamConverter.from_paths(
                source=temp_source,
                destination=temp_dir,
                source_base_path=temp_source.parent,
                config_path=empty_config_path,
            )
        error_msg = str(exc_info.value)
        assert "Invalid configuration format" in error_msg

    def test_constructor_handles_nested_dicts(self):
        """Constructor converts nested dictionaries to configuration objects."""
        # Create a dictionary with nested dictionaries
        config_dict = {
            "conversion": {
                "frontmatter_format": "yaml",
                "convert_tags": True,
                "link_format": "[[${title}]]",
                "preserve_path_structure": True,
                "preserve_link_descriptions": True,
                "link_description_format": "[[${title}|${description}]]",
            },
            "attachments": {
                "copy_attachments": True,
                "attachment_folder": "test_assets",
            },
            "formatting": {
                "convert_tables": False,
                "convert_code_blocks": True,
                "convert_latex": False,
            },
        }

        # Use constructor directly with nested dictionaries
        config = ConverterConfig(**config_dict)  # type: ignore[arg-type]

        # Create expected configuration
        expected = ConverterConfig(
            conversion=ConversionConfig(
                frontmatter_format="yaml",
                convert_tags=True,
                link_format="[[${title}]]",
                preserve_path_structure=True,
                preserve_link_descriptions=True,
                link_description_format="[[${title}|${description}]]",
            ),
            attachments=AttachmentsConfig(
                copy_attachments=True,
                attachment_folder="test_assets",
            ),
            formatting=FormattingConfig(
                convert_tables=False,
                convert_code_blocks=True,
                convert_latex=False,
            ),
        )

        assert config == expected

    def test_generate_frontmatter_data(self, temp_source, temp_dir):
        """Generate frontmatter data from node metadata."""
        from pathlib import Path

        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test node with various metadata
        node = OrgRoamNode(
            id="test-node",
            file_path=Path("/path/to/file.org"),
            title="Test Node",
            level=1,
            pos=100,
            olp=["Parent", "Child"],
            properties={"CREATED": "2023-01-15"},  # Should be ignored
            tags=["tag1", "tag2"],
            aliases=["alias1", "alias2"],
            refs=["http:example.com", "https:test.org"],
        )

        # Create converter with default config
        config = ConverterConfig(
            conversion=ConversionConfig(
                convert_tags=True,
            ),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
        )

        # Generate frontmatter data
        frontmatter_data = converter._generate_frontmatter_data(node, config.conversion)

        # Verify frontmatter contents
        assert frontmatter_data["tags"] == ["tag1", "tag2"]
        assert frontmatter_data["aliases"] == ["alias1", "alias2"]
        assert frontmatter_data["links"] == ["http:example.com", "https:test.org"]

    def test_generate_frontmatter_data_without_metadata(self, temp_source, temp_dir):
        """
        Generate frontmatter data when aliases, tags, and refs are missing.
        """
        from pathlib import Path

        from org_roam_to_obsidian.database import OrgRoamNode

        # Create test node without aliases, tags, and refs
        node = OrgRoamNode(
            id="test-node",
            file_path=Path("/path/to/file.org"),
            title="Test Node",
            level=1,
            pos=100,
            olp=[],
            properties={},
            tags=[],
            aliases=[],
            refs=[],
        )

        # Create converter with default config
        config = ConverterConfig(
            conversion=ConversionConfig(
                convert_tags=True,
            ),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )

        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            source_base_path=temp_source.parent,
        )

        # Generate frontmatter data
        frontmatter_data = converter._generate_frontmatter_data(node, config.conversion)

        # Verify frontmatter contents
        assert frontmatter_data == {}

    def test_format_frontmatter_yaml(self, temp_source, temp_dir):
        """Format frontmatter data as YAML."""
        # Create converter with default config
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=DEFAULT_CONFIG,
            source_base_path=temp_source.parent,
        )

        # Test data
        data = {
            "title": "Test Document",
            "tags": ["test", "example"],
            "aliases": ["Test", "Example Document"],
        }

        # Format as YAML
        yaml_frontmatter = converter._format_frontmatter(data, "yaml")

        # Verify format is correct
        assert yaml_frontmatter.startswith("---\n")
        assert yaml_frontmatter.endswith("---\n\n")
        assert "title: Test Document" in yaml_frontmatter
        assert "- test" in yaml_frontmatter
        assert "- example" in yaml_frontmatter
        assert "- Test" in yaml_frontmatter
        assert "- Example Document" in yaml_frontmatter

    def test_format_frontmatter_json(self, temp_source, temp_dir):
        """Format frontmatter data as JSON."""
        # Create converter with default config
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=DEFAULT_CONFIG,
            source_base_path=temp_source.parent,
        )

        # Test data
        data = {
            "title": "Test Document",
            "tags": ["test", "example"],
            "aliases": ["Test", "Example Document"],
        }

        # Format as JSON
        json_frontmatter = converter._format_frontmatter(data, "json")

        # Verify format is correct
        assert json_frontmatter.startswith("---\n")
        assert json_frontmatter.endswith("\n---\n\n")
        assert '"title": "Test Document"' in json_frontmatter
        assert '"tags": [' in json_frontmatter
        assert '"test"' in json_frontmatter
        assert '"example"' in json_frontmatter
        assert '"aliases": [' in json_frontmatter
        assert '"Test"' in json_frontmatter
        assert '"Example Document"' in json_frontmatter

    def test_convert_org_roam_links(self, temp_source, temp_dir):
        """Convert org-roam ID links to Obsidian title links."""
        # Create converter with default config
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=DEFAULT_CONFIG,
            source_base_path=temp_source.parent,
        )

        # Create test nodes
        from org_roam_to_obsidian.database import OrgRoamNode

        test_nodes = {
            "node1": OrgRoamNode(
                id="node1",
                file_path=Path("/path/to/node1.org"),
                title="First Node",
                level=1,
                pos=0,
            ),
            "node2": OrgRoamNode(
                id="node2",
                file_path=Path("/path/to/node2.org"),
                title="Second Node",
                level=1,
                pos=0,
            ),
        }

        # Test markdown content with org-roam links
        markdown_content = """
# Test Document

This is a test document with several org-roam links:

Link without description: <id:node1>
Link with description: [Custom Description](id:node2)
Link with description matching title: [First Node](id:node1)
Link to unknown node: <id:unknown>
Link to unknown node with description: [Missing Link](id:unknown2)
"""

        # Convert the links
        converted_content = converter._convert_org_roam_links(
            markdown_content,
            test_nodes,
            converter.config.conversion,
        )

        expected_converted_content = """
# Test Document

This is a test document with several org-roam links:

Link without description: [[First Node]]
Link with description: [[Second Node|Custom Description]]
Link with description matching title: [[First Node]]
Link to unknown node: <id:unknown>
Link to unknown node with description: [[Missing Link]]
"""
        assert converted_content == expected_converted_content
