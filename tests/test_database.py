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

    assert len(files) == 2

    expected_files = [
        OrgRoamFile(
            file_path=Path("/path/to/file1.org"),
            hash="hash1",
            atime="(25821 50943 0 0)",
            mtime="(25821 50943 0 0)",
        ),
        OrgRoamFile(
            file_path=Path("/path/to/file2.org"),
            hash="hash2",
            atime="(26316 12970 0 0)",
            mtime="(26316 12970 0 0)",
        ),
    ]

    assert files == expected_files


def test_get_all_nodes(sample_db_path):
    """Get all nodes from the database."""
    db = OrgRoamDatabase(Path(sample_db_path))
    nodes = list(db.get_all_nodes())

    assert len(nodes) == 3

    # Check node1
    node1 = next(node for node in nodes if node.id == "node1")
    assert node1.file_path == Path("/path/to/file1.org")
    assert node1.title == "Node 1"
    assert node1.level == 1
    assert node1.pos == 100
    assert node1.olp == ["Parent", "Child"]
    assert node1.properties == {"CREATED": "20220101"}
    assert set(node1.tags) == {"tag1", "tag2"}
    assert set(node1.aliases) == {"alias1", "alias2"}
    assert node1.refs == []

    # Check node2
    node2 = next(node for node in nodes if node.id == "node2")
    assert node2.file_path == Path("/path/to/file1.org")
    assert node2.title == "Node 2"
    assert node2.level == 2
    assert node2.pos == 200
    assert node2.olp == ["Parent", "Child", "Grandchild"]
    assert node2.properties == {"CREATED": "20220102"}
    assert node2.tags == ["tag3"]
    assert node2.aliases == []
    assert set(node2.refs) == {"ref1", "ref2"}

    # Check node3
    node3 = next(node for node in nodes if node.id == "node3")
    assert node3.file_path == Path("/path/to/file2.org")
    assert node3.title == "Node 3"
    assert node3.level == 1
    assert node3.pos == 100
    assert node3.olp == []
    assert node3.properties == {"CREATED": "20220103"}
    assert node3.tags == []
    assert node3.aliases == ["alias3"]
    assert node3.refs == []


def test_get_node_by_id(sample_db_path):
    """Get a specific node by ID."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get existing node
    node = db.get_node_by_id("node1")
    assert node is not None
    assert node.id == "node1"
    assert node.file_path == Path("/path/to/file1.org")
    assert node.title == "Node 1"
    assert set(node.tags) == {"tag1", "tag2"}
    assert set(node.aliases) == {"alias1", "alias2"}

    # Get non-existent node
    node = db.get_node_by_id("nonexistent")
    assert node is None


def test_get_links(sample_db_path):
    """Get all links from the database."""
    db = OrgRoamDatabase(Path(sample_db_path))
    links = list(db.get_links())

    assert len(links) == 2

    assert links[0].source_id == "node1"
    assert links[0].dest_id == "node2"
    assert links[0].type == "id"
    assert links[0].properties == {"position": 100}

    assert links[1].source_id == "node2"
    assert links[1].dest_id == "node3"
    assert links[1].type == "id"
    assert links[1].properties == {"position": 200}


def test_get_links_for_node(sample_db_path):
    """Get links for a specific node."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get links for node1
    links = list(db.get_links_for_node("node1"))
    assert len(links) == 1
    assert links[0].source_id == "node1"
    assert links[0].dest_id == "node2"

    # Get links for node with no outgoing links
    links = list(db.get_links_for_node("node3"))
    assert len(links) == 0


def test_get_backlinks_for_node(sample_db_path):
    """Get backlinks for a specific node."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get backlinks for node2
    backlinks = list(db.get_backlinks_for_node("node2"))
    assert len(backlinks) == 1
    assert backlinks[0].source_id == "node1"
    assert backlinks[0].dest_id == "node2"

    # Get backlinks for node with no incoming links
    backlinks = list(db.get_backlinks_for_node("node1"))
    assert len(backlinks) == 0


def test_get_file_nodes(sample_db_path):
    """Get all nodes from a specific file."""
    db = OrgRoamDatabase(Path(sample_db_path))

    # Get nodes for file1
    nodes = list(db.get_file_nodes(Path("/path/to/file1.org")))
    assert len(nodes) == 2
    assert nodes[0].id == "node1"
    assert nodes[1].id == "node2"

    # Get nodes for file2
    nodes = list(db.get_file_nodes(Path("/path/to/file2.org")))
    assert len(nodes) == 1
    assert nodes[0].id == "node3"

    # Get nodes for non-existent file
    nodes = list(db.get_file_nodes(Path("/path/to/nonexistent.org")))
    assert len(nodes) == 0


def test_create_id_to_filename_map(sample_db_path):
    """Create a mapping from node IDs to file paths."""
    db = OrgRoamDatabase(Path(sample_db_path))
    id_to_file = db.create_id_to_filename_map()

    assert len(id_to_file) == 3
    assert id_to_file["node1"] == Path("/path/to/file1.org")
    assert id_to_file["node2"] == Path("/path/to/file1.org")
    assert id_to_file["node3"] == Path("/path/to/file2.org")


def test_context_manager(sample_db_path):
    """Test that the database can be used as a context manager."""
    with OrgRoamDatabase(Path(sample_db_path)) as db:
        assert db is not None
        files = list(db.get_all_files())
        assert len(files) == 2
