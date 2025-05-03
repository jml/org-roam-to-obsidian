import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from org_roam_to_obsidian.converter import (
    AttachmentsConfig,
    ConversionConfig,
    ConverterConfig,
    DEFAULT_CONFIG,
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
preserve_creation_date = true
frontmatter_format = "yaml"
convert_tags = true
link_format = "[[${filename}]]"

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


class TestConfigClasses:
    """Test the configuration dataclasses."""

    def test_conversion_config_defaults(self):
        """Default initialization of ConversionConfig sets expected values."""
        config = ConversionConfig()
        expected = ConversionConfig(
            preserve_creation_date=True,
            frontmatter_format="yaml",
            convert_tags=True,
            link_format="[[${filename}]]",
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
        assert "Link format must contain ${filename} placeholder" in error_msg

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
            dry_run=True,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            dry_run=True,
        )
        assert converter == expected

    def test_from_paths(self, temp_source, temp_dir):
        """Factory method creates converter from source and destination paths."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            dry_run=True,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=DEFAULT_CONFIG,
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
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            config=config,
            dry_run=False,
        )
        assert converter == expected

    def test_from_toml_config(self, temp_source, temp_dir, temp_config_file):
        """Loading from TOML config file overrides default configuration values."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            config_path=temp_config_file,
        )

        # Create the expected config with the values from the TOML file
        expected_config = ConverterConfig(
            conversion=ConversionConfig(
                preserve_creation_date=True,
                frontmatter_format="yaml",
                convert_tags=True,
                link_format="[[${filename}]]",
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
            dry_run=False,
        )

        assert converter == expected

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
                "preserve_creation_date": True,
                "convert_tags": True,
                "link_format": "[[${filename}]]",
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
                preserve_creation_date=True,
                convert_tags=True,
                link_format="[[${filename}]]",
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
