"""
Query service for AST operations.

This service provides all query, search, and diff operations on the AST.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from ...ast import (
    ASTNode,
    NodeType,
    SerializationVisitor,
    DiffVisitor,
    SearchVisitor,
    hash_tree,
)
from ...parser import load_ableton_xml, build_ast
from ..ast_helpers import ASTBuilder

logger = logging.getLogger(__name__)


class QueryService:
    """
    Service for querying and searching the AST.

    Provides operations for:
    - Serialization (JSON export)
    - Node finding (by ID, type, predicate)
    - Diff computation
    - Project statistics
    """

    def __init__(self, server):
        """
        Initialize query service.

        Args:
            server: ASTServer instance providing current_ast reference
        """
        self.server = server
        self.serializer = SerializationVisitor()
        self.diff_visitor = DiffVisitor()
        self.search_visitor = SearchVisitor()
        self.logger = logging.getLogger(f"{__name__}.QueryService")

    @property
    def ast(self):
        """Get current AST from server."""
        return self.server.current_ast

    def get_ast_json(self, include_hash: bool = True) -> str:
        """
        Get the current AST as JSON.

        Args:
            include_hash: Whether to include node hashes

        Returns:
            JSON string representation

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        serializer = SerializationVisitor(include_hash=include_hash)
        return serializer.to_json(self.ast)

    def find_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a node by its ID.

        Args:
            node_id: The node ID to search for

        Returns:
            Serialized node or None if not found

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        node = self.search_visitor.find_by_id(self.ast, node_id)
        if node:
            return self.serializer.visit(node)
        return None

    def find_nodes_by_type(self, node_type_str: str) -> List[Dict[str, Any]]:
        """
        Find all nodes of a specific type.

        Args:
            node_type_str: Node type as string (e.g., "track", "device")

        Returns:
            List of serialized nodes

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            return []

        nodes = self.search_visitor.find_by_type(self.ast, node_type)
        return [self.serializer.visit(node) for node in nodes]

    def query_nodes(self, predicate_str: str) -> List[Dict[str, Any]]:
        """
        Query nodes using a simple predicate.

        Example predicates:
        - "name == 'Audio'"
        - "index > 5"

        Args:
            predicate_str: Simple predicate expression

        Returns:
            List of matching nodes

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        # Simple predicate parser (can be expanded)
        # For now, just support attribute equality
        def predicate(node: ASTNode) -> bool:
            try:
                # Very basic evaluation - expand as needed
                if "==" in predicate_str:
                    key, value = predicate_str.split("==")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    return node.attributes.get(key) == value
                return False
            except Exception:
                return False

        nodes = self.search_visitor.find_by_predicate(self.ast, predicate)
        return [self.serializer.visit(node) for node in nodes]

    def diff_with_file(self, other_file: Path) -> List[Dict[str, Any]]:
        """
        Compute diff between current AST and another file.

        Args:
            other_file: Path to another .als or .xml file

        Returns:
            List of changes

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        # Load the other file
        tree = load_ableton_xml(other_file)
        raw_ast = build_ast(tree.getroot())
        other_ast = ASTBuilder.build_node_tree(raw_ast, tree.getroot())
        hash_tree(other_ast)

        # Compute diff
        return self.diff_visitor.diff(self.ast, other_ast)

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get high-level information about the loaded project.

        Returns:
            Dictionary with project statistics

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.ast:
            raise RuntimeError("No project loaded")

        tracks = self.search_visitor.find_by_type(self.ast, NodeType.TRACK)
        devices = self.search_visitor.find_by_type(self.ast, NodeType.DEVICE)
        clips = self.search_visitor.find_by_type(self.ast, NodeType.CLIP)
        scenes = self.search_visitor.find_by_type(self.ast, NodeType.SCENE)
        file_refs = self.search_visitor.find_by_type(self.ast, NodeType.FILE_REF)

        return {
            "file": str(self.server.current_file) if self.server.current_file else None,
            "root_hash": self.ast.hash,
            "num_tracks": len(tracks),
            "num_devices": len(devices),
            "num_clips": len(clips),
            "num_scenes": len(scenes),
            "num_file_refs": len(file_refs),
            "track_names": [t.attributes.get("name") for t in tracks],
        }
