"""
AST module for Ableton Live projects.

This module provides:
- Node class definitions for representing project structure
- Visitor patterns for traversal, diffing, and serialization
- Incremental hashing for change detection
"""

from .node import (
    ASTNode,
    NodeType,
    ProjectNode,
    TrackNode,
    DeviceNode,
    ClipNode,
    FileRefNode,
    SceneNode,
    ParameterNode,
)

from .visitor import (
    ASTVisitor,
    SerializationVisitor,
    DiffVisitor,
    PrettyPrintVisitor,
    SearchVisitor,
)

from .hashing import (
    NodeHasher,
    hash_tree,
)

__all__ = [
    # Nodes
    "ASTNode",
    "NodeType",
    "ProjectNode",
    "TrackNode",
    "DeviceNode",
    "ClipNode",
    "FileRefNode",
    "SceneNode",
    "ParameterNode",
    # Visitors
    "ASTVisitor",
    "SerializationVisitor",
    "DiffVisitor",
    "PrettyPrintVisitor",
    "SearchVisitor",
    # Hashing
    "NodeHasher",
    "hash_tree",
]
