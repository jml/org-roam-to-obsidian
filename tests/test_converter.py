import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from org_roam_to_obsidian.converter import (
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
        """Test ConversionConfig default values."""
        config = ConversionConfig()
        assert config.preserve_creation_date is True
        assert config.frontmatter_format == "yaml"
        assert config.convert_tags is True
        assert config.link_format == "[[${filename}]]"

    def test_conversion_config_validation(self):
        """Test validation for ConversionConfig."""
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
        """Test AttachmentsConfig default values."""
        config = AttachmentsConfig()
        assert config.copy_attachments is True
        assert config.attachment_folder == "assets"

    def test_attachments_config_validation(self):
        """Test validation for AttachmentsConfig."""
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
        """Test FormattingConfig default values."""
        config = FormattingConfig()
        assert config.convert_tables is True
        assert config.convert_code_blocks is True
        assert config.convert_latex is True

    def test_converter_config_defaults(self):
        """Test ConverterConfig default values."""
        config = ConverterConfig(
            conversion=ConversionConfig(),
            attachments=AttachmentsConfig(),
            formatting=FormattingConfig(),
        )
        assert isinstance(config.conversion, ConversionConfig)
        assert isinstance(config.attachments, AttachmentsConfig)
        assert isinstance(config.formatting, FormattingConfig)


class TestOrgRoamConverter:
    """Test the OrgRoamConverter class."""

    def test_init(self, temp_source, temp_dir):
        """Test converter initialization."""
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

        assert converter.source == temp_source
        assert converter.destination == temp_dir
        assert converter.dry_run is True

    def test_from_paths(self, temp_source, temp_dir):
        """Test the from_paths factory method."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            dry_run=True,
        )

        assert converter.source == temp_source
        assert converter.destination == temp_dir
        assert converter.dry_run is True

    def test_default_config(self, temp_source, temp_dir):
        """Test default configuration is set correctly."""
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

        assert isinstance(converter.config, ConverterConfig)
        assert converter.config.conversion.frontmatter_format == "yaml"
        assert converter.config.attachments.attachment_folder == "assets"

    def test_from_toml_config(self, temp_source, temp_dir, temp_config_file):
        """Test loading configuration from a TOML file."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            config_path=temp_config_file,
        )

        assert isinstance(converter.config, ConverterConfig)
        assert converter.config.conversion.frontmatter_format == "yaml"
        # Check custom value from the TOML file
        assert converter.config.attachments.attachment_folder == "custom_assets"
        assert converter.config.formatting.convert_code_blocks is False

    def test_invalid_config_validation(self, temp_source, temp_dir):
        """Test that invalid configurations are rejected."""
        # Create an invalid config file
        invalid_config_content = """
        [conversion]
        frontmatter_format = "invalid"
        
        [attachments]
        attachment_folder = "invalid/path"
        """

        invalid_config_path = temp_dir / "invalid_config.toml"
        with open(invalid_config_path, "w") as f:
            f.write(invalid_config_content)

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            OrgRoamConverter.from_paths(
                source=temp_source,
                destination=temp_dir,
                config_path=invalid_config_path,
            )

        error_msg = str(exc_info.value)
        assert (
            "Frontmatter format must be one of" in error_msg
            or "Attachment folder cannot contain path separators" in error_msg
        )
