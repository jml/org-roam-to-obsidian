import pytest
from pathlib import Path
import tempfile

from org_roam_to_obsidian.converter import OrgRoamConverter


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

    def test_default_config(self, temp_source, temp_dir):
        """Test default configuration is set correctly."""
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
        )

        assert "conversion" in converter.config
        assert "attachments" in converter.config
        assert "formatting" in converter.config

        # Check a few specific config values
        assert converter.config["conversion"]["frontmatter_format"] == "yaml"
        assert converter.config["attachments"]["attachment_folder"] == "assets"
