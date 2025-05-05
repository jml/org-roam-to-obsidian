"""Tests for the database module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from org_roam_to_obsidian.database import (
    OrgRoamDatabase,
    OrgRoamFile,
    OrgRoamLink,
    OrgRoamNode,
)


@pytest.fixture
def sample_db_path():
    """Create a temporary SQLite database with org-roam schema for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
        # Create a new SQLite database
        conn = sqlite3.connect(temp_db.name)

        # Create tables matching org-roam schema
        conn.executescript("""
            -- Create files table
            CREATE TABLE files (
                file TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                atime REAL,
                mtime REAL
            );

            -- Create nodes table
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                file TEXT NOT NULL,
                title TEXT,
                level INTEGER,
                pos INTEGER NOT NULL,
                properties TEXT,
                olp TEXT,
                FOREIGN KEY(file) REFERENCES files(file) ON DELETE CASCADE
            );

            -- Create tags table
            CREATE TABLE tags (
                node_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY(node_id, tag),
                FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
            );

            -- Create aliases table
            CREATE TABLE aliases (
                node_id TEXT NOT NULL,
                alias TEXT NOT NULL,
                PRIMARY KEY(node_id, alias),
                FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
            );

            -- Create refs table
            CREATE TABLE refs (
                node_id TEXT NOT NULL,
                ref TEXT NOT NULL,
                PRIMARY KEY(node_id, ref),
                FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
            );

            -- Create links table
            CREATE TABLE links (
                source TEXT NOT NULL,
                dest TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT,
                PRIMARY KEY(source, dest, type),
                FOREIGN KEY(source) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY(dest) REFERENCES nodes(id) ON DELETE CASCADE
            );
        """)

        # Insert sample data for testing
        # Sample files
        conn.executemany(
            "INSERT INTO files (file, hash, atime, mtime) VALUES (?, ?, ?, ?)",
            [
                (
                    "/path/to/file1.org",
                    "hash1",
                    "(25821 50943 0 0)",
                    "(25821 50943 0 0)",
                ),
                (
                    "/path/to/file2.org",
                    "hash2",
                    "(26316 12970 0 0)",
                    "(26316 12970 0 0)",
                ),
                (
                    '"/path/to/quoted_file.org"',  # Note the quotes around the path
                    "hash3",
                    "(26316 12970 0 0)",
                    "(26316 12970 0 0)",
                ),
            ],
        )

        # Sample nodes
        conn.executemany(
            """INSERT INTO nodes (id, file, title, level, pos, properties, olp)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "node1",
                    "/path/to/file1.org",
                    "Node 1",
                    1,
                    100,
                    '{"CREATED": "20220101"}',
                    '["Parent", "Child"]',
                ),
                (
                    "node2",
                    "/path/to/file1.org",
                    "Node 2",
                    2,
                    200,
                    '{"CREATED": "20220102"}',
                    '["Parent", "Child", "Grandchild"]',
                ),
                (
                    "node3",
                    "/path/to/file2.org",
                    "Node 3",
                    1,
                    100,
                    '{"CREATED": "20220103"}',
                    "[]",
                ),
                (
                    "node4",
                    '"/path/to/quoted_file.org"',  # Note the quotes around the path
                    "Node 4",
                    1,
                    100,
                    '{"CREATED": "20220104"}',
                    "[]",
                ),
            ],
        )

        # Sample tags
        conn.executemany(
            "INSERT INTO tags (node_id, tag) VALUES (?, ?)",
            [
                ("node1", "tag1"),
                ("node1", "tag2"),
                ("node2", "tag3"),
            ],
        )

        # Sample aliases
        conn.executemany(
            "INSERT INTO aliases (node_id, alias) VALUES (?, ?)",
            [
                ("node1", "alias1"),
                ("node1", "alias2"),
                ("node3", "alias3"),
            ],
        )

        # Sample refs
        conn.executemany(
            "INSERT INTO refs (node_id, ref) VALUES (?, ?)",
            [
                ("node2", "ref1"),
                ("node2", "ref2"),
            ],
        )

        # Sample links
        conn.executemany(
            "INSERT INTO links (source, dest, type, properties) VALUES (?, ?, ?, ?)",
            [
                ("node1", "node2", "id", '{"position": 100}'),
                ("node2", "node3", "id", '{"position": 200}'),
            ],
        )

        conn.commit()
        conn.close()

        yield temp_db.name


def test_orgroamnode_creation():
    """Create an OrgRoamNode with all fields."""
    node = OrgRoamNode(
        id="abc123",
        file_path=Path("/path/to/file.org"),
        title="Test Node",
        level=1,
        pos=100,
        olp=["Parent", "Child"],
        properties={"CREATED": "20220101"},
        tags=["tag1", "tag2"],
        aliases=["alias1", "alias2"],
        refs=["ref1", "ref2"],
    )

    expected = OrgRoamNode(
        id="abc123",
        file_path=Path("/path/to/file.org"),
        title="Test Node",
        level=1,
        pos=100,
        olp=["Parent", "Child"],
        properties={"CREATED": "20220101"},
        tags=["tag1", "tag2"],
        aliases=["alias1", "alias2"],
        refs=["ref1", "ref2"],
    )

    assert node == expected


def test_orgroamlink_creation():
    """Create an OrgRoamLink with all fields."""
    link = OrgRoamLink(
        source_id="abc123",
        dest_id="def456",
        type="id",
        properties={"position": 200},
    )

    expected = OrgRoamLink(
        source_id="abc123",
        dest_id="def456",
        type="id",
        properties={"position": 200},
    )

    assert link == expected


def test_orgroamfile_creation():
    """Create an OrgRoamFile with all fields."""
    file = OrgRoamFile(
        file_path=Path("/path/to/file.org"),
        hash="abcdef1234567890",
        atime="(26316 12970 418226 295000)",
        mtime="(25821 50943 0 0)",
    )

    expected = OrgRoamFile(
        file_path=Path("/path/to/file.org"),
        hash="abcdef1234567890",
        atime="(26316 12970 418226 295000)",
        mtime="(25821 50943 0 0)",
    )

    assert file == expected


def test_orgroamdatabase_init_file_not_found():
    """Initialize OrgRoamDatabase with a non-existent database file."""
    db_path = Path("/non/existent/file.db")

    with pytest.raises(FileNotFoundError):
        OrgRoamDatabase(db_path)


def test_get_all_files(sample_db_path):
    """Get all files from the database."""
    db = OrgRoamDatabase(Path(sample_db_path))
    files = list(db.get_all_files())

    # After our fix, we should get all 3 files, including the one with quotes
    assert len(files) == 3

    # The files come back in alphabetical order from the SQL query
    # So we should sort them by file path for comparison
    files_by_path = {str(f.file_path): f for f in files}

    # Verify we have all expected paths
    assert "/path/to/file1.org" in files_by_path
    assert "/path/to/file2.org" in files_by_path
    assert "/path/to/quoted_file.org" in files_by_path

    # Check files match expected objects
    expected_file1 = OrgRoamFile(
        file_path=Path("/path/to/file1.org"),
        hash="hash1",
        atime="(25821 50943 0 0)",
        mtime="(25821 50943 0 0)",
    )

    expected_file2 = OrgRoamFile(
        file_path=Path("/path/to/file2.org"),
        hash="hash2",
        atime="(26316 12970 0 0)",
        mtime="(26316 12970 0 0)",
    )

    expected_quoted_file = OrgRoamFile(
        file_path=Path("/path/to/quoted_file.org"),
        hash="hash3",
        atime="(26316 12970 0 0)",
        mtime="(26316 12970 0 0)",
    )

    assert files_by_path["/path/to/file1.org"] == expected_file1
    assert files_by_path["/path/to/file2.org"] == expected_file2
    assert files_by_path["/path/to/quoted_file.org"] == expected_quoted_file


def test_get_all_nodes(sample_db_path):
    """Get all nodes from the database."""
    db = OrgRoamDatabase(Path(sample_db_path))
    nodes = list(db.get_all_nodes())

    assert len(nodes) == 4  # Now includes node4 with the quoted file path

    # Define expected nodes
    expected_node1 = OrgRoamNode(
        id="node1",
        file_path=Path("/path/to/file1.org"),
        title="Node 1",
        level=1,
        pos=100,
        olp=["Parent", "Child"],
        properties={"CREATED": "20220101"},
        tags=["tag1", "tag2"],
        aliases=["alias1", "alias2"],
        refs=[],
    )

    expected_node2 = OrgRoamNode(
        id="node2",
        file_path=Path("/path/to/file1.org"),
        title="Node 2",
        level=2,
        pos=200,
        olp=["Parent", "Child", "Grandchild"],
        properties={"CREATED": "20220102"},
        tags=["tag3"],
        aliases=[],
        refs=["ref1", "ref2"],
    )

    expected_node3 = OrgRoamNode(
        id="node3",
        file_path=Path("/path/to/file2.org"),
        title="Node 3",
        level=1,
        pos=100,
        olp=[],
        properties={"CREATED": "20220103"},
        tags=[],
        aliases=["alias3"],
        refs=[],
    )

    expected_node4 = OrgRoamNode(
        id="node4",
        file_path=Path("/path/to/quoted_file.org"),
        title="Node 4",
        level=1,
        pos=100,
        olp=[],
        properties={"CREATED": "20220104"},
        tags=[],
        aliases=[],
        refs=[],
    )

    # The order of nodes might vary, so we need to find them by ID
    node1 = next(node for node in nodes if node.id == "node1")
    node2 = next(node for node in nodes if node.id == "node2")
    node3 = next(node for node in nodes if node.id == "node3")
    node4 = next(node for node in nodes if node.id == "node4")

    # Compare full objects
    assert node1 == expected_node1
    assert node2 == expected_node2
    assert node3 == expected_node3
    assert node4 == expected_node4


def test_get_node_by_id(sample_db_path):
    """Get a specific node by ID."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get existing node
    node = db.get_node_by_id("node1")
    assert node is not None

    expected_node = OrgRoamNode(
        id="node1",
        file_path=Path("/path/to/file1.org"),
        title="Node 1",
        level=1,
        pos=100,
        olp=["Parent", "Child"],
        properties={"CREATED": "20220101"},
        tags=["tag1", "tag2"],
        aliases=["alias1", "alias2"],
        refs=[],
    )

    assert node == expected_node

    # Get non-existent node
    node = db.get_node_by_id("nonexistent")
    assert node is None


def test_get_links(sample_db_path):
    """Get all links from the database."""
    db = OrgRoamDatabase(Path(sample_db_path))
    links = list(db.get_links())

    assert len(links) == 2

    expected_link1 = OrgRoamLink(
        source_id="node1",
        dest_id="node2",
        type="id",
        properties={"position": 100},
    )

    expected_link2 = OrgRoamLink(
        source_id="node2",
        dest_id="node3",
        type="id",
        properties={"position": 200},
    )

    assert links[0] == expected_link1
    assert links[1] == expected_link2


def test_get_links_for_node(sample_db_path):
    """Get links for a specific node."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get links for node1
    links = list(db.get_links_for_node("node1"))
    assert len(links) == 1

    expected_link = OrgRoamLink(
        source_id="node1",
        dest_id="node2",
        type="id",
        properties={"position": 100},
    )

    assert links[0] == expected_link

    # Get links for node with no outgoing links
    links = list(db.get_links_for_node("node3"))
    assert len(links) == 0


def test_get_backlinks_for_node(sample_db_path):
    """Get backlinks for a specific node."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get backlinks for node2
    backlinks = list(db.get_backlinks_for_node("node2"))
    assert len(backlinks) == 1

    expected_backlink = OrgRoamLink(
        source_id="node1",
        dest_id="node2",
        type="id",
        properties={"position": 100},
    )

    assert backlinks[0] == expected_backlink

    # Get backlinks for node with no incoming links
    backlinks = list(db.get_backlinks_for_node("node1"))
    assert len(backlinks) == 0


def test_get_file_nodes(sample_db_path):
    """Get all nodes from a specific file."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get nodes for file1
    nodes = list(db.get_file_nodes(Path("/path/to/file1.org")))
    assert len(nodes) == 2

    expected_node1 = OrgRoamNode(
        id="node1",
        file_path=Path("/path/to/file1.org"),
        title="Node 1",
        level=1,
        pos=100,
        olp=["Parent", "Child"],
        properties={"CREATED": "20220101"},
        tags=["tag1", "tag2"],
        aliases=["alias1", "alias2"],
        refs=[],
    )

    expected_node2 = OrgRoamNode(
        id="node2",
        file_path=Path("/path/to/file1.org"),
        title="Node 2",
        level=2,
        pos=200,
        olp=["Parent", "Child", "Grandchild"],
        properties={"CREATED": "20220102"},
        tags=["tag3"],
        aliases=[],
        refs=["ref1", "ref2"],
    )

    assert nodes[0] == expected_node1
    assert nodes[1] == expected_node2

    # Get nodes for file2
    nodes = list(db.get_file_nodes(Path("/path/to/file2.org")))
    assert len(nodes) == 1

    expected_node3 = OrgRoamNode(
        id="node3",
        file_path=Path("/path/to/file2.org"),
        title="Node 3",
        level=1,
        pos=100,
        olp=[],
        properties={"CREATED": "20220103"},
        tags=[],
        aliases=["alias3"],
        refs=[],
    )

    assert nodes[0] == expected_node3

    # Get nodes for non-existent file
    nodes = list(db.get_file_nodes(Path("/path/to/nonexistent.org")))
    assert len(nodes) == 0


def test_create_id_to_filename_map(sample_db_path):
    """Create a mapping from node IDs to file paths."""
    db = OrgRoamDatabase(Path(sample_db_path))
    id_to_file = db.create_id_to_filename_map()

    assert len(id_to_file) == 4  # Includes all nodes

    expected_mapping = {
        "node1": Path("/path/to/file1.org"),
        "node2": Path("/path/to/file1.org"),
        "node3": Path("/path/to/file2.org"),
        "node4": Path("/path/to/quoted_file.org"),
    }

    assert id_to_file == expected_mapping


def test_context_manager(sample_db_path):
    """Test that the database can be used as a context manager."""
    with OrgRoamDatabase(Path(sample_db_path)) as db:
        assert db is not None
        files = list(db.get_all_files())
        assert len(files) == 3  # Now includes the file with quoted path


def test_create_file_to_nodes_map(sample_db_path):
    """Create a mapping from file paths to their associated nodes."""
    db = OrgRoamDatabase(Path(sample_db_path))
    file_to_nodes = db.create_file_to_nodes_map()

    # Check that the paths are the expected ones
    file_paths = list(file_to_nodes.keys())
    expected_paths = [
        Path("/path/to/file1.org"),
        Path("/path/to/file2.org"),
        Path("/path/to/quoted_file.org"),
    ]
    assert set(str(p) for p in file_paths) == set(str(p) for p in expected_paths)

    # Check that file1 has 2 nodes, in the correct order by position
    file1_path = Path("/path/to/file1.org")
    assert len(file_to_nodes[file1_path]) == 2
    assert file_to_nodes[file1_path][0].id == "node1"  # pos=100
    assert file_to_nodes[file1_path][1].id == "node2"  # pos=200

    # Check that file2 has 1 node
    file2_path = Path("/path/to/file2.org")
    assert len(file_to_nodes[file2_path]) == 1
    assert file_to_nodes[file2_path][0].id == "node3"

    # Check that quoted_file has 1 node
    quoted_file_path = Path("/path/to/quoted_file.org")
    assert len(file_to_nodes[quoted_file_path]) == 1
    assert file_to_nodes[quoted_file_path][0].id == "node4"


def test_quoted_file_paths_bug(sample_db_path, tmp_path):
    """Demonstrate the bug with quoted file paths in the database."""
    # Connect to the database
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get all raw file paths directly from the database
    cursor = db.conn.execute("SELECT file FROM files ORDER BY file")
    raw_paths = [row["file"] for row in cursor]

    # Verify that there are quoted paths in the database
    assert any('"' in path for path in raw_paths)

    # Find a quoted path in the database
    quoted_path = next(path for path in raw_paths if '"' in path)

    # Create the file
    test_file = tmp_path / "test_file.org"
    test_file.write_text("Test content")

    # Demonstrate the issue: when checking file existence with quoted paths

    # The file at the quoted path doesn't exist
    assert not Path(quoted_path).exists()

    # The file with the same name without quotes would exist (if we had created it)
    # For this test, we're using a temporary file to demonstrate the principle
    assert test_file.exists()

    # This demonstrates the core issue: when the database contains quoted paths,
    # using Path(row["file"]) creates paths with quotes that don't match real files
    # The converter's _convert_file method fails with "source_file_not_found"
    # because src_file.exists() returns False for these quoted paths


def test_strip_quotes_from_file_paths(sample_db_path, tmp_path):
    """Test that quotes are properly stripped from file paths."""
    # Connect to the database
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get all raw file paths directly from the database
    cursor = db.conn.execute("SELECT file FROM files ORDER BY file")
    raw_paths = [row["file"] for row in cursor]

    # Find a quoted path
    quoted_path = next((path for path in raw_paths if '"' in path), None)
    assert quoted_path is not None, "No quoted path found in test database"

    # Get OrgRoamFile objects using our fixed implementation
    files = list(db.get_all_files())

    # Find the file object that corresponds to the quoted path
    quoted_file = next(
        (f for f in files if f.file_path.name == Path(quoted_path.strip('"')).name),
        None,
    )
    assert quoted_file is not None, "Could not find file with quoted path in results"

    # Create a temporary file that matches the path after quotes are stripped
    test_file = tmp_path / quoted_file.file_path.name
    test_file.write_text("Test content")

    # Create paths to test with
    buggy_path_obj = Path(quoted_path)  # Has quotes, won't match real files
    fixed_path_obj = quoted_file.file_path  # From our fixed implementation

    # The buggy path (with quotes) shouldn't exist
    assert not buggy_path_obj.exists()

    # Create a file at the fixed path location (in tmp_path) to simulate a real file
    fixed_test_path = tmp_path / fixed_path_obj.name
    fixed_test_path.write_text("Test content")

    # This path should exist
    assert fixed_test_path.exists()

    # Verify quotes were stripped correctly - check the full OrgRoamFile object
    expected_file = OrgRoamFile(
        file_path=Path(quoted_path.strip('"')),
        hash="hash3",
        atime="(26316 12970 0 0)",
        mtime="(26316 12970 0 0)",
    )

    assert quoted_file == expected_file

    # This confirms:
    # 1. Our fix correctly strips quotes from paths in get_all_files()
    # 2. The resulting paths don't contain quotes and would match real files
    # 3. The buggy paths with quotes would fail existence checks
