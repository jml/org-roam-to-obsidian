"""
Module for interacting with the org-roam SQLite database.

This module provides classes and functions for querying the org-roam SQLite
database and extracting metadata about nodes, files, links, tags, and other
elements needed for conversion to Obsidian.
"""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import field
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterator,
    Mapping,
    Tuple,
    TypeVar,
)

from pydantic.dataclasses import dataclass

from org_roam_to_obsidian.elisp import parse_single_elisp
from org_roam_to_obsidian.elisp_parser import (
    Expression,
    ParseError,
    parse_elisp_alist_to_dict,
    parse_elisp_int,
    parse_elisp_list,
    parse_elisp_path,
    parse_elisp_plist_to_dict,
    parse_elisp_string,
    parse_elisp_time,
)
from org_roam_to_obsidian.logging import get_logger

log = get_logger(__name__)

# Type variable for field values
T = TypeVar("T")


class Field(Generic[T], ABC):
    """Base class for field parsers."""

    name: str

    @abstractmethod
    def parse(self, row: Mapping[str, Any]) -> T:
        """Parse a field from a database row."""
        pass


@dataclass(frozen=True)
class RequiredField(Field[T]):
    """Declarative field definition for required fields."""

    name: str  # Field name in the database row
    parser: Callable[[Expression], T]  # Function to parse the field

    def parse(self, row: Mapping[str, Any]) -> T:
        """
        Parse a required field from a database row.

        Args:
            row: Database row (sqlite3.Row or dictionary)

        Returns:
            Parsed value of type T

        Raises:
            ParseError: If the field is missing or can't be parsed
        """
        # Get raw value using direct access which works with both dict and sqlite3.Row
        try:
            raw_value = row[self.name]
        except (KeyError, IndexError):
            raise ParseError(f"Required field {self.name} is missing")

        if raw_value is None:
            raise ParseError(f"Required field {self.name} is missing")

        # Parse elisp expression
        expr = parse_single_elisp(str(raw_value))
        if expr is None:
            raise ParseError(f"Failed to parse {self.name}: {raw_value}")

        # Parse expression to destination type
        try:
            return self.parser(expr)
        except ParseError as e:
            raise ParseError(f"Failed to parse {repr(raw_value)}: {e}")


@dataclass(frozen=True)
class OptionalField(Field[T]):
    """Declarative field definition for optional fields."""

    name: str  # Field name in the database row
    parser: Callable[[Expression], T]  # Function to parse the field
    default: T  # Default value if field is missing or None

    def parse(self, row: Mapping[str, Any]) -> T:
        """
        Parse an optional field from a database row.

        Args:
            row: Database row (sqlite3.Row or dictionary)

        Returns:
            Parsed value of type T, or the default value if missing/unparseable
        """
        # Get raw value using direct access which works with both dict and sqlite3.Row
        try:
            raw_value = row[self.name]
        except (KeyError, IndexError):
            return self.default

        if raw_value is None:
            return self.default

        # Parse elisp expression
        expr = parse_single_elisp(str(raw_value))
        if expr is None:
            return self.default

        # Parse expression to destination type
        try:
            return self.parser(expr)
        except ParseError:
            return self.default


def parse_fields(
    row: Mapping[str, Any], fields: dict[str, Field[Any]]
) -> dict[str, Any]:
    """Parse multiple fields from a row according to field definitions."""
    return {
        field_name: field_def.parse(row) for field_name, field_def in fields.items()
    }


def parse_string_list(data: Expression) -> list[str]:
    """
    Convert olp from Elisp expression to list of strings.

    Args:
        data: Elisp expression representing an olp

    Returns:
        List of strings from the olp

    Raises:
        ParseError: If parsing fails
    """
    objects = parse_elisp_list(data)
    olp = [o for o in objects if isinstance(o, str)]
    if len(olp) < len(objects):
        raise TypeError(f"Found unexpected non-string in olp: {objects}")
    return olp


def parse_strings(strings: list[str]) -> list[str]:
    output = []
    for s in strings:
        expr = parse_single_elisp(s)
        if expr is None:
            raise ParseError(f"Could not parse list of emacs expressions: {strings}")
        output.append(parse_elisp_string(expr))
    return output


@dataclass(frozen=True)
class OrgRoamNode:
    """Represents a node in the org-roam database."""

    id: str
    file_path: Path
    title: str
    level: int
    pos: int
    olp: list[str] = field(default_factory=list)
    properties: dict[str, object] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)

    # Define field parsers as class variables
    FIELDS: ClassVar[dict[str, Field[Any]]] = {
        "id": RequiredField[str](name="id", parser=parse_elisp_string),
        "file_path": RequiredField[Path](name="file", parser=parse_elisp_path),
        "title": RequiredField[str](name="title", parser=parse_elisp_string),
        "level": RequiredField[int](name="level", parser=parse_elisp_int),
        "pos": RequiredField[int](name="pos", parser=parse_elisp_int),
        "olp": OptionalField[list[str]](
            name="olp", parser=parse_string_list, default=[]
        ),
        "properties": OptionalField[dict[str, object]](
            name="properties",
            parser=parse_elisp_alist_to_dict,
            default={},
        ),
    }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OrgRoamNode":
        """
        Create an OrgRoamNode from a database row.

        Args:
            row: A dict-like object with column names as keys

        Returns:
            An OrgRoamNode instance
        """
        # Parse fields according to definitions
        parsed_values = parse_fields(row, cls.FIELDS)

        # Handle special cases like tags which need custom processing
        try:
            tags = row["tags"].split(",") if row["tags"] else []
        except (KeyError, IndexError):
            tags = []
        tags = parse_strings(tags)

        # Aliases and refs are already parsed by _get_node_aliases and _get_node_refs
        try:
            aliases = row["aliases"]
        except (KeyError, IndexError):
            aliases = []

        try:
            refs = row["refs"]
        except (KeyError, IndexError):
            refs = []

        # Add these to our parsed values
        parsed_values.update({"tags": tags, "aliases": aliases, "refs": refs})

        return cls(**parsed_values)


@dataclass(frozen=True)
class OrgRoamRef:
    """Represents an external reference from a node in the org-roam database."""

    ref: str
    type: str

    # Define field parsers as class variables
    FIELDS: ClassVar[dict[str, Field[Any]]] = {
        "ref": RequiredField[str](name="ref", parser=parse_elisp_string),
        "type": RequiredField[str](name="type", parser=parse_elisp_string),
    }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OrgRoamRef":
        """
        Create an OrgRoamRef from a database row.

        Args:
            row: A dict-like object with column names as keys

        Returns:
            An OrgRoamRef instance
        """
        return cls(**parse_fields(row, cls.FIELDS))

    def format(self) -> str:
        """
        Format the reference as a string.

        Returns:
            The formatted reference string (type:ref)
        """
        return f"{self.type}:{self.ref}"


@dataclass(frozen=True)
class OrgRoamLink:
    """Represents a link between nodes in the org-roam database."""

    source_id: str
    dest_id: str
    type: str
    properties: dict[str, object] = field(default_factory=dict)

    # Define field parsers as class variables
    FIELDS: ClassVar[dict[str, Field[Any]]] = {
        "source_id": RequiredField[str](name="source", parser=parse_elisp_string),
        "dest_id": RequiredField[str](name="dest", parser=parse_elisp_string),
        "type": RequiredField[str](name="type", parser=parse_elisp_string),
        "properties": OptionalField[dict[str, object]](
            name="properties",
            parser=parse_elisp_plist_to_dict,
            default={},
        ),
    }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OrgRoamLink":
        """
        Create an OrgRoamLink from a database row.

        Args:
            row: A dict-like object with column names as keys

        Returns:
            An OrgRoamLink instance
        """
        return cls(**parse_fields(row, cls.FIELDS))


@dataclass(frozen=True)
class OrgRoamFile:
    """Represents a file in the org-roam database."""

    file_path: Path
    hash: str
    atime: Tuple[
        int, int, int, int
    ]  # Emacs Lisp time tuple: (HIGH LOW MICROSEC PICOSEC)
    mtime: Tuple[
        int, int, int, int
    ]  # Emacs Lisp time tuple: (HIGH LOW MICROSEC PICOSEC)

    # Define field parsers as class variables
    FIELDS: ClassVar[dict[str, Field[Any]]] = {
        "file_path": RequiredField[Path](name="file", parser=parse_elisp_path),
        "hash": RequiredField[str](name="hash", parser=parse_elisp_string),
        "atime": OptionalField[Tuple[int, int, int, int]](
            name="atime",
            parser=parse_elisp_time,
            default=(0, 0, 0, 0),
        ),
        "mtime": OptionalField[Tuple[int, int, int, int]](
            name="mtime",
            parser=parse_elisp_time,
            default=(0, 0, 0, 0),
        ),
    }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OrgRoamFile":
        """
        Create an OrgRoamFile from a database row.

        Args:
            row: A dict-like object with column names as keys

        Returns:
            An OrgRoamFile instance
        """
        return cls(**parse_fields(row, cls.FIELDS))


class OrgRoamDatabase:
    """Interface to the org-roam SQLite database."""

    def __init__(self, db_path: Path) -> None:
        """
        Initialize the database connection.

        Args:
            db_path: Path to the org-roam SQLite database
        """
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        log.info("connecting_to_database", path=str(db_path))

        # Enable foreign keys and convert Path objects to strings
        self.conn = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )

        # Use Row factory for dict-like access
        self.conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Close the database connection."""
        if self.conn is not None:
            self.conn.close()

    def __enter__(self) -> "OrgRoamDatabase":
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close database connection when exiting context."""
        self.close()

    def get_all_files(self) -> Iterator[OrgRoamFile]:
        """
        Get all files tracked by org-roam.

        Returns:
            Iterator of OrgRoamFile objects
        """
        cursor = self.conn.execute(
            """
            SELECT file, hash, atime, mtime
            FROM files
            ORDER BY file
            """
        )

        for row in cursor:
            yield OrgRoamFile.from_row(row)

    def get_all_nodes(self) -> Iterator[OrgRoamNode]:
        """
        Get all nodes from the org-roam database.

        Returns:
            Iterator of OrgRoamNode objects
        """
        cursor = self.conn.execute(
            """
            SELECT n.id, n.file, n.title, n.level, n.pos, n.properties,
                   group_concat(t.tag, ',') as tags,
                   n.olp
            FROM nodes n
            LEFT JOIN tags t ON n.id = t.node_id
            GROUP BY n.id
            ORDER BY n.file, n.pos
            """
        )

        for row in cursor:
            # Get node aliases
            aliases = self._get_node_aliases(row["id"])

            # Get node references
            refs = self._get_node_refs(row["id"])

            # Create a row dict with all data
            row_dict = dict(row)
            row_dict["aliases"] = aliases
            row_dict["refs"] = refs

            yield OrgRoamNode.from_row(row_dict)

    def _get_node_aliases(self, node_id: str) -> list[str]:
        """
        Get aliases for a specific node.

        Args:
            node_id: The ID of the node

        Returns:
            List of alias strings
        """
        cursor = self.conn.execute(
            """
            SELECT alias
            FROM aliases
            WHERE node_id = ?
            """,
            (node_id,),
        )

        return parse_strings([row["alias"] for row in cursor])

    def _get_node_refs(self, node_id: str) -> list[str]:
        """
        Get external references for a specific node.

        Args:
            node_id: The ID of the node

        Returns:
            List of reference strings with type prefix
        """
        cursor = self.conn.execute(
            """
            SELECT ref, type
            FROM refs
            WHERE node_id = ?
            """,
            (node_id,),
        )

        formatted_refs = []
        for row in cursor:
            # Use the OrgRoamRef class to parse and format the reference
            ref = OrgRoamRef.from_row(row)
            formatted_refs.append(ref.format())

        return formatted_refs

    def get_node_by_id(self, node_id: str) -> OrgRoamNode | None:
        """
        Get a specific node by its ID.

        Args:
            node_id: The ID of the node to retrieve

        Returns:
            OrgRoamNode object or None if not found
        """
        node_id = f'"{node_id}"'
        cursor = self.conn.execute(
            """
            SELECT n.id, n.file, n.title, n.level, n.pos, n.properties, n.olp
            FROM nodes n
            WHERE n.id = ?
            """,
            (node_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Get node tags
        tags_cursor = self.conn.execute(
            """
            SELECT tag
            FROM tags
            WHERE node_id = ?
            """,
            (node_id,),
        )
        tags = [tag_row["tag"] for tag_row in tags_cursor]

        # Get node aliases
        aliases = self._get_node_aliases(node_id)

        # Get node references
        refs = self._get_node_refs(node_id)

        # Create a row dict with all data
        row_dict = dict(row)
        row_dict["tags"] = ",".join(tags) if tags else ""
        row_dict["aliases"] = aliases
        row_dict["refs"] = refs

        return OrgRoamNode.from_row(row_dict)

    def get_links(self) -> Iterator[OrgRoamLink]:
        """
        Get all links between nodes.

        Returns:
            Iterator of OrgRoamLink objects
        """
        cursor = self.conn.execute(
            """
            SELECT source, dest, type, properties
            FROM links
            ORDER BY source, dest
            """
        )

        for row in cursor:
            yield OrgRoamLink.from_row(row)

    def get_links_for_node(self, node_id: str) -> Iterator[OrgRoamLink]:
        """
        Get all links where the specified node is the source.

        Args:
            node_id: ID of the source node

        Returns:
            Iterator of OrgRoamLink objects
        """
        # Format the node_id as an Elisp string (quoted) to match database storage
        elisp_node_id = f'"{node_id}"'
        cursor = self.conn.execute(
            """
            SELECT source, dest, type, properties
            FROM links
            WHERE source = ?
            ORDER BY dest
            """,
            (elisp_node_id,),
        )

        for row in cursor:
            yield OrgRoamLink.from_row(row)

    def get_backlinks_for_node(self, node_id: str) -> Iterator[OrgRoamLink]:
        """
        Get all links where the specified node is the destination.

        Args:
            node_id: ID of the destination node

        Returns:
            Iterator of OrgRoamLink objects
        """
        # Format the node_id as an Elisp string (quoted) to match database storage
        elisp_node_id = f'"{node_id}"'
        cursor = self.conn.execute(
            """
            SELECT source, dest, type, properties
            FROM links
            WHERE dest = ?
            ORDER BY source
            """,
            (elisp_node_id,),
        )

        for row in cursor:
            yield OrgRoamLink.from_row(row)

    def get_file_nodes(self, file_path: Path) -> Iterator[OrgRoamNode]:
        """
        Get all nodes from a specific file.

        Args:
            file_path: Path to the org file

        Returns:
            Iterator of OrgRoamNode objects
        """
        # We need to convert the file_path to an Elisp string for comparison
        # This would ideally be done with proper parameter binding, but SQLite
        # doesn't directly support binding to LIKE clauses with wildcards
        elisp_file_path = f'"{str(file_path)}"'

        cursor = self.conn.execute(
            """
            SELECT n.id, n.file, n.title, n.level, n.pos, n.properties, n.olp
            FROM nodes n
            WHERE n.file = ?
            ORDER BY n.pos
            """,
            (elisp_file_path,),
        )

        for row in cursor:
            # Get node tags
            tags_cursor = self.conn.execute(
                """
                SELECT tag
                FROM tags
                WHERE node_id = ?
                """,
                (row["id"],),
            )
            tags = [tag_row["tag"] for tag_row in tags_cursor]

            # Get node aliases
            aliases = self._get_node_aliases(row["id"])

            # Get node references
            refs = self._get_node_refs(row["id"])

            # Create a row dict with all data
            row_dict = dict(row)
            row_dict["tags"] = ",".join(tags) if tags else ""
            row_dict["aliases"] = aliases
            row_dict["refs"] = refs

            yield OrgRoamNode.from_row(row_dict)

    def create_id_to_filename_map(self) -> dict[str, Path]:
        """
        Create a mapping from node IDs to relative file paths.

        This is useful for converting links between nodes.

        Returns:
            Dictionary mapping node IDs to their file paths
        """
        cursor = self.conn.execute(
            """
            SELECT id, file
            FROM nodes
            """
        )

        id_field = OrgRoamNode.FIELDS["id"]
        file_field = OrgRoamNode.FIELDS["file_path"]

        result: dict[str, Path] = {}
        for row in cursor:
            id_value = id_field.parse(row)
            file_value = file_field.parse(row)
            result[id_value] = file_value

        return result

    def create_file_to_nodes_map(self) -> dict[Path, list[OrgRoamNode]]:
        """
        Create a mapping from file paths to their associated nodes.

        This is useful for extracting metadata for frontmatter generation.

        Returns:
            Dictionary mapping file paths to lists of their associated nodes
        """
        # Get all nodes and group them by file path
        file_to_nodes: dict[Path, list[OrgRoamNode]] = {}

        for node in self.get_all_nodes():
            file_path = node.file_path
            if file_path not in file_to_nodes:
                file_to_nodes[file_path] = []
            file_to_nodes[file_path].append(node)

        # Sort nodes within each file by position
        for nodes in file_to_nodes.values():
            nodes.sort(key=lambda n: n.pos)

        return file_to_nodes
