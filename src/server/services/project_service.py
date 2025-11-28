"""
Project service for AST loading and management.

This service handles project file loading, AST construction,
and project metadata.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from ...ast import ProjectNode, hash_tree
from ...parser import load_ableton_xml, build_ast
from ..ast_helpers import ASTBuilder

logger = logging.getLogger(__name__)


class ProjectService:
    """
    Service for project loading and management.

    Provides operations for:
    - Loading .als files
    - Building AST from XML
    - Broadcasting loaded projects
    """

    def __init__(self, server):
        """
        Initialize project service.

        Args:
            server: ASTServer instance
        """
        self.server = server
        self.logger = logging.getLogger(f"{__name__}.ProjectService")

    def load_project(self, file_path: Path, broadcast: bool = True) -> Dict[str, Any]:
        """
        Load an Ableton Live project file and build its AST.

        Args:
            file_path: Path to .als or .xml file
            broadcast: Whether to broadcast full AST to WebSocket clients (default: True)
                       Set to False if you're computing diffs manually

        Returns:
            Dictionary with status and basic project info
        """
        self.server.current_file = file_path

        # Load and parse XML
        tree = load_ableton_xml(file_path)
        raw_ast = build_ast(tree.getroot())

        # Convert to structured AST nodes
        self.server.current_ast = self._build_node_tree(raw_ast, tree.getroot())

        # Compute hashes
        hash_tree(self.server.current_ast)

        # Broadcast to WebSocket clients if enabled
        if broadcast and self.server.websocket_server and self.server.websocket_server.is_running():
            asyncio.create_task(
                self.server.websocket_server.broadcast_full_ast(
                    self.server.current_ast,
                    str(file_path)
                )
            )

        return {
            "status": "success",
            "file": str(file_path),
            "root_hash": self.server.current_ast.hash,
        }

    def _build_node_tree(self, raw_ast: Dict, xml_root) -> ProjectNode:
        """
        Convert the raw dictionary AST to structured node objects.

        This bridges the gap between the parser's dict output
        and the AST node structure.

        Args:
            raw_ast: Raw AST dictionary from parser
            xml_root: XML root element

        Returns:
            ProjectNode representing the AST root
        """
        return ASTBuilder.build_node_tree(raw_ast, xml_root)
