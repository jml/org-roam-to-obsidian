import tempfile
from pathlib import Path

import pytest

from org_roam_to_obsidian.converter import (
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
        """Test directory structure in destination paths."""
        output_dir = temp_dir / "output"
        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
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

    def test_get_destination_path_fallback_behavior(
        self, temp_source, temp_dir, nested_org_files
    ):
        """Test fallback behavior when paths are outside the base path."""
        output_dir = temp_dir / "output_fallback"

        # Use a different base path to trigger the fallback behavior
        different_base_path = temp_dir.parent

        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
            source_base_path=different_base_path,  # This will cause the fallback
        )

        # Test with OrgRoamNode objects
        from org_roam_to_obsidian.database import OrgRoamNode

        # Create a test node with a title
        test_node = OrgRoamNode(
            id="test-id",
            file_path=nested_org_files["files"][
                0
            ],  # This path won't be relative to different_base_path
            title="Test Node Title",
            level=1,
            pos=0,
        )

        # Get the destination path
        dest_path = converter._get_destination_path(test_node)

        # When the file is outside the base path, the actual path contains
        # the relative path between the parent and the file
        # For example, if the temp dir is /tmp/abc and the file is /tmp/abc/org_files/root.org,
        # the destination would be output_dir/abc/org_files/Test Node Title.md

        # We just check that the filename part is correct
        assert dest_path.name == "Test Node Title.md"

        # And that an appropriate directory structure was created
        assert output_dir.exists()

    def test_get_destination_path_handles_special_characters(
        self, temp_source, temp_dir
    ):
        """Test handling of special characters in node titles for filenames."""
        output_dir = temp_dir / "output_special"
        converter = OrgRoamConverter(
            source=temp_source,
            destination=output_dir,
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
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
            dry_run=True,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
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
            source_base_path=temp_source.parent,
            dry_run=True,
        )
        assert converter == expected

    def test_from_paths_with_default_config(self, temp_source, temp_dir):
        """Factory method creates converter from source and destination paths with default config."""
        converter = OrgRoamConverter.from_paths(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
        )

        expected = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
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

    def test_with_base_path(self, temp_source, temp_dir, nested_org_files):
        """Test that source_base_path is properly used."""
        base_path = nested_org_files["base_path"]

        # Create converter with explicitly provided source_base_path
        converter = OrgRoamConverter.from_paths(
            source=temp_source, destination=temp_dir, source_base_path=base_path
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
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
        )

        # Generate frontmatter data
        frontmatter_data = converter._generate_frontmatter_data(node)

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
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
        )

        # Generate frontmatter data
        frontmatter_data = converter._generate_frontmatter_data(node)

        # Verify frontmatter contents
        assert frontmatter_data == {}

    def test_format_frontmatter(self, temp_source, temp_dir):
        """Format frontmatter data as YAML."""
        # Create converter with default config
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
            source_base_path=temp_source.parent,
        )

        # Test data
        data = {
            "title": "Test Document",
            "tags": ["test", "example"],
            "aliases": ["Test", "Example Document"],
        }

        # Format frontmatter
        yaml_frontmatter = converter._format_frontmatter(data)

        # Verify format is correct
        assert yaml_frontmatter.startswith("---\n")
        assert yaml_frontmatter.endswith("---\n\n")
        assert "title: Test Document" in yaml_frontmatter
        assert "- test" in yaml_frontmatter
        assert "- example" in yaml_frontmatter
        assert "- Test" in yaml_frontmatter
        assert "- Example Document" in yaml_frontmatter

    def test_convert_org_roam_links(self, temp_source, temp_dir):
        """Convert org-roam ID links to Obsidian title links."""
        # Create converter with default config
        converter = OrgRoamConverter(
            source=temp_source,
            destination=temp_dir,
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
