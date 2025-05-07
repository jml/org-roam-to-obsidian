"""
Module for interacting with the org-roam SQLite database.

This module provides classes and functions for querying the org-roam SQLite
database and extracting metadata about nodes, files, links, tags, and other
elements needed for conversion to Obsidian.
"""

import sqlite3
from dataclasses import field
from pathlib import Path
from typing import Any, Iterator, Tuple

from pydantic.dataclasses import dataclass

from org_roam_to_obsidian.elisp import parse_elisp
from org_roam_to_obsidian.elisp_parser import (
    ParseError,
    parse_elisp_list,
    parse_elisp_path,
    parse_elisp_plist_to_dict,
    parse_elisp_time,
)
from org_roam_to_obsidian.logging import get_logger

log = get_logger(__name__)


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


@dataclass(frozen=True)
class OrgRoamLink:
    """Represents a link between nodes in the org-roam database."""

    source_id: str
    dest_id: str
    type: str
    properties: dict[str, object] = field(default_factory=dict)


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
            try:
                # Parse file path as Elisp string
                file_path = parse_elisp_path(parse_elisp(row["file"])[0])

                # Parse time values
                atime_tuple = (0, 0, 0, 0)
                mtime_tuple = (0, 0, 0, 0)

                try:
                    if row["atime"]:
                        atime_expr = parse_elisp(row["atime"])[0]
                        atime_tuple = parse_elisp_time(atime_expr)
                except ParseError:
                    log.warning(
                        "failed_to_parse_atime",
                        file=str(file_path),
                        atime=row["atime"],
                    )

                try:
                    if row["mtime"]:
                        mtime_expr = parse_elisp(row["mtime"])[0]
                        mtime_tuple = parse_elisp_time(mtime_expr)
                except ParseError:
                    log.warning(
                        "failed_to_parse_mtime",
                        file=str(file_path),
                        mtime=row["mtime"],
                    )

                yield OrgRoamFile(
                    file_path=file_path,
                    hash=row["hash"],
                    atime=atime_tuple,
                    mtime=mtime_tuple,
                )
            except ParseError as e:
                log.warning(
                    "failed_to_parse_file_path",
                    path=row["file"],
                    error=str(e),
                )

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
            try:
                # Convert properties from Elisp string to dict
                properties = {}
                if row["properties"]:
                    try:
                        expressions = parse_elisp(row["properties"])
                        if expressions:
                            properties = parse_elisp_plist_to_dict(expressions[0])
                    except ParseError:
                        log.warning(
                            "failed_to_parse_properties",
                            node_id=row["id"],
                            properties=row["properties"],
                        )

                # Convert tags from comma-separated string to list
                tags = []
                if row["tags"]:
                    tags = row["tags"].split(",")

                # Get node aliases
                aliases = self._get_node_aliases(row["id"])

                # Get node references
                refs = self._get_node_refs(row["id"])

                # Convert file path from Elisp string
                file_path = parse_elisp_path(parse_elisp(row["file"])[0])

                olp = parse_olp(row["olp"]) if row["olp"] else []

                yield OrgRoamNode(
                    id=row["id"],
                    file_path=file_path,
                    title=row["title"],
                    level=row["level"],
                    pos=row["pos"],
                    olp=olp,
                    properties=properties,
                    tags=tags,
                    aliases=aliases,
                    refs=refs,
                )
            except ParseError as e:
                log.warning(
                    "failed_to_parse_node",
                    node_id=row["id"],
                    error=str(e),
                )

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

        return [row["alias"] for row in cursor]

    def _get_node_refs(self, node_id: str) -> list[str]:
        """
        Get external references for a specific node.

        Args:
            node_id: The ID of the node

        Returns:
            List of reference strings
        """
        cursor = self.conn.execute(
            """
            SELECT ref
            FROM refs
            WHERE node_id = ?
            """,
            (node_id,),
        )

        return [row["ref"] for row in cursor]

    def get_node_by_id(self, node_id: str) -> OrgRoamNode | None:
        """
        Get a specific node by its ID.

        Args:
            node_id: The ID of the node to retrieve

        Returns:
            OrgRoamNode object or None if not found
        """
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

        try:
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

            # Convert properties from Elisp to dict
            properties = {}
            if row["properties"]:
                try:
                    expressions = parse_elisp(row["properties"])
                    if expressions:
                        properties = parse_elisp_plist_to_dict(expressions[0])
                except ParseError:
                    log.warning(
                        "failed_to_parse_properties",
                        node_id=row["id"],
                        properties=row["properties"],
                    )

            # Convert file path from Elisp string
            file_path = parse_elisp_path(parse_elisp(row["file"])[0])

            # Convert olp from Elisp array to list of strings
            olp = parse_olp(row["olp"]) if row["olp"] else []

            return OrgRoamNode(
                id=row["id"],
                file_path=file_path,
                title=row["title"],
                level=row["level"],
                pos=row["pos"],
                olp=olp,
                properties=properties,
                tags=tags,
                aliases=aliases,
                refs=refs,
            )
        except ParseError as e:
            log.warning(
                "failed_to_parse_node",
                node_id=row["id"],
                error=str(e),
            )
            return None

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
            # Convert properties from Elisp to dict
            properties = {}
            if row["properties"]:
                try:
                    expressions = parse_elisp(row["properties"])
                    if expressions:
                        properties = parse_elisp_plist_to_dict(expressions[0])
                except ParseError:
                    log.warning(
                        "failed_to_parse_link_properties",
                        source=row["source"],
                        dest=row["dest"],
                        properties=row["properties"],
                    )

            yield OrgRoamLink(
                source_id=row["source"],
                dest_id=row["dest"],
                type=row["type"],
                properties=properties,
            )

    def get_links_for_node(self, node_id: str) -> Iterator[OrgRoamLink]:
        """
        Get all links where the specified node is the source.

        Args:
            node_id: ID of the source node

        Returns:
            Iterator of OrgRoamLink objects
        """
        cursor = self.conn.execute(
            """
            SELECT source, dest, type, properties
            FROM links
            WHERE source = ?
            ORDER BY dest
            """,
            (node_id,),
        )

        for row in cursor:
            # Convert properties from Elisp to dict
            properties = {}
            if row["properties"]:
                try:
                    expressions = parse_elisp(row["properties"])
                    if expressions:
                        properties = parse_elisp_plist_to_dict(expressions[0])
                except ParseError:
                    log.warning(
                        "failed_to_parse_link_properties",
                        source=row["source"],
                        dest=row["dest"],
                        properties=row["properties"],
                    )

            yield OrgRoamLink(
                source_id=row["source"],
                dest_id=row["dest"],
                type=row["type"],
                properties=properties,
            )

    def get_backlinks_for_node(self, node_id: str) -> Iterator[OrgRoamLink]:
        """
        Get all links where the specified node is the destination.

        Args:
            node_id: ID of the destination node

        Returns:
            Iterator of OrgRoamLink objects
        """
        cursor = self.conn.execute(
            """
            SELECT source, dest, type, properties
            FROM links
            WHERE dest = ?
            ORDER BY source
            """,
            (node_id,),
        )

        for row in cursor:
            # Convert properties from Elisp to dict
            properties = {}
            if row["properties"]:
                try:
                    expressions = parse_elisp(row["properties"])
                    if expressions:
                        properties = parse_elisp_plist_to_dict(expressions[0])
                except ParseError:
                    log.warning(
                        "failed_to_parse_link_properties",
                        source=row["source"],
                        dest=row["dest"],
                        properties=row["properties"],
                    )

            yield OrgRoamLink(
                source_id=row["source"],
                dest_id=row["dest"],
                type=row["type"],
                properties=properties,
            )

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
            try:
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

                # Convert properties from Elisp to dict
                properties = {}
                if row["properties"]:
                    try:
                        expressions = parse_elisp(row["properties"])
                        if expressions:
                            properties = parse_elisp_plist_to_dict(expressions[0])
                    except ParseError:
                        log.warning(
                            "failed_to_parse_properties",
                            node_id=row["id"],
                            properties=row["properties"],
                        )

                # Convert file path from Elisp string
                parsed_file_path = parse_elisp_path(parse_elisp(row["file"])[0])

                # Convert olp from Elisp array to list of strings
                olp = parse_olp(row["olp"]) if row["olp"] else []

                yield OrgRoamNode(
                    id=row["id"],
                    file_path=parsed_file_path,
                    title=row["title"],
                    level=row["level"],
                    pos=row["pos"],
                    olp=olp,
                    properties=properties,
                    tags=tags,
                    aliases=aliases,
                    refs=refs,
                )
            except ParseError as e:
                log.warning(
                    "failed_to_parse_node",
                    node_id=row["id"],
                    error=str(e),
                )

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

        id_to_file: dict[str, Path] = {}
        for row in cursor:
            try:
                # Parse file path as Elisp string
                file_path = parse_elisp_path(parse_elisp(row["file"])[0])
                id_to_file[row["id"]] = file_path
            except ParseError:
                log.warning(
                    "failed_to_parse_file_path_for_id",
                    node_id=row["id"],
                    file=row["file"],
                )

        return id_to_file

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


def parse_olp(data: str) -> list[str]:
    """
    Convert olp from Elisp string to list of strings.

    Args:
        data: Elisp string representation of an olp

    Returns:
        List of strings from the olp

    Raises:
        ParseError: If parsing fails
    """
    try:
        expressions = parse_elisp(data)
        if not expressions:
            return []

        expr = expressions[0]
        objects = parse_elisp_list(expr)
        olp = [o for o in objects if isinstance(o, str)]
        if len(olp) < len(objects):
            raise TypeError(f"Found unexpected non-string in olp: {objects}")
        return olp
    except (ParseError, TypeError, SyntaxError) as e:
        raise ParseError(f"Failed to parse olp: {e}") from e
