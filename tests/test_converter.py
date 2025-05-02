import tempfile
from pathlib import Path

import pytest

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


class TestConfigClasses:
    """Test the configuration dataclasses."""

    def test_conversion_config_defaults(self):
        """Test ConversionConfig default values."""
        config = ConversionConfig()
        assert config.preserve_creation_date is True
        assert config.frontmatter_format == "yaml"
        assert config.convert_tags is True
        assert config.link_format == "[[${filename}]]"

    def test_attachments_config_defaults(self):
        """Test AttachmentsConfig default values."""
        config = AttachmentsConfig()
        assert config.copy_attachments is True
        assert config.attachment_folder == "assets"

    def test_formatting_config_defaults(self):
        """Test FormattingConfig default values."""
        config = FormattingConfig()
        assert config.convert_tables is True
        assert config.convert_code_blocks is True
        assert config.convert_latex is True

    def test_converter_config_defaults(self):
        """Test ConverterConfig default values."""
        config = ConverterConfig()
        assert isinstance(config.conversion, ConversionConfig)
        assert isinstance(config.attachments, AttachmentsConfig)
        assert isinstance(config.formatting, FormattingConfig)


class TestOrgRoamConverter:
    """Test the OrgRoamConverter class."""

    def test_init(self, temp_source, temp_dir):
        """Test converter initialization."""
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
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
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
        )

        assert isinstance(converter.config, ConverterConfig)
        assert converter.config.conversion.frontmatter_format == "yaml"
        assert converter.config.attachments.attachment_folder == "assets"
