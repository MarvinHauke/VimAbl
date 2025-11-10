"""
Incremental hashing for AST nodes.

This module computes content-based hashes for each AST node, enabling:
- Fast change detection
- Incremental updates
- Cache invalidation
- Content-addressable storage
"""

import hashlib
import json
from typing import Any, Dict
from .node import ASTNode


class NodeHasher:
    """
    Computes SHA-256 hashes for AST nodes.

    The hash is computed from:
    - Node type
    - Node attributes
    - Hashes of all children (for incremental hashing)
    """

    def __init__(self, algorithm: str = "sha256"):
        """
        Initialize the hasher.

        Args:
            algorithm: Hash algorithm to use (default: sha256)
        """
        self.algorithm = algorithm

    def hash_node(self, node: ASTNode, recursive: bool = True) -> str:
        """
        Compute hash for a node.

        Args:
            node: The AST node to hash
            recursive: If True, recursively hash children first

        Returns:
            Hexadecimal hash string
        """
        if recursive:
            # First hash all children
            for child in node.children:
                if child.hash is None:
                    child.hash = self.hash_node(child, recursive=True)

        # Compute hash for this node
        node.hash = self._compute_hash(node)
        return node.hash

    def _compute_hash(self, node: ASTNode) -> str:
        """
        Compute the hash value for a single node.

        The hash includes:
        - Node type
        - Node ID
        - Attributes (sorted for consistency)
        - Child hashes (not full child content)
        """
        hasher = hashlib.new(self.algorithm)

        # Include node type
        hasher.update(node.node_type.value.encode('utf-8'))

        # Include node ID
        if node.id:
            hasher.update(node.id.encode('utf-8'))

        # Include attributes (sorted for deterministic hashing)
        attrs_str = self._serialize_attributes(node.attributes)
        hasher.update(attrs_str.encode('utf-8'))

        # Include child hashes (not full content - this is what makes it incremental)
        for child in node.children:
            if child.hash:
                hasher.update(child.hash.encode('utf-8'))

        return hasher.hexdigest()

    def _serialize_attributes(self, attributes: Dict[str, Any]) -> str:
        """
        Serialize attributes to a deterministic string.

        Uses JSON serialization with sorted keys.
        """
        # Filter out None values and sort keys
        filtered = {k: v for k, v in attributes.items() if v is not None}
        return json.dumps(filtered, sort_keys=True, default=str)

    def verify_hash(self, node: ASTNode) -> bool:
        """
        Verify that a node's hash matches its current content.

        Returns:
            True if hash is valid, False otherwise
        """
        if node.hash is None:
            return False

        stored_hash = node.hash
        computed_hash = self._compute_hash(node)
        return stored_hash == computed_hash

    def update_hash(self, node: ASTNode, propagate_up: bool = True) -> str:
        """
        Update the hash of a node after it has been modified.

        Args:
            node: The node to update
            propagate_up: If True, also update ancestor hashes

        Returns:
            The new hash value
        """
        # Recompute this node's hash
        node.hash = self._compute_hash(node)

        # Propagate up to parent
        if propagate_up and node.parent:
            self.update_hash(node.parent, propagate_up=True)

        return node.hash

    def find_modified_nodes(self, old_tree: ASTNode, new_tree: ASTNode) -> Dict[str, tuple]:
        """
        Find all nodes that have been modified by comparing hashes.

        Args:
            old_tree: The old AST
            new_tree: The new AST

        Returns:
            Dictionary mapping node paths to (old_node, new_node) tuples
        """
        # Ensure both trees are hashed
        if old_tree.hash is None:
            self.hash_node(old_tree)
        if new_tree.hash is None:
            self.hash_node(new_tree)

        modified = {}
        self._compare_nodes(old_tree, new_tree, [], modified)
        return modified

    def _compare_nodes(
        self,
        old: ASTNode,
        new: ASTNode,
        path: list,
        modified: Dict[str, tuple]
    ) -> None:
        """Recursively compare nodes by hash."""
        current_path = "/".join(path + [old.id or f"{old.node_type.value}"])

        # If hashes differ, this node or its descendants changed
        if old.hash != new.hash:
            # Check if this specific node changed (not just descendants)
            old_content = self._serialize_attributes(old.attributes)
            new_content = self._serialize_attributes(new.attributes)

            if old_content != new_content:
                modified[current_path] = (old, new)

            # Recursively check children
            old_children_by_id = {c.id: c for c in old.children if c.id}
            new_children_by_id = {c.id: c for c in new.children if c.id}

            common_ids = set(old_children_by_id.keys()) & set(new_children_by_id.keys())
            for child_id in common_ids:
                self._compare_nodes(
                    old_children_by_id[child_id],
                    new_children_by_id[child_id],
                    path + [old.id or f"{old.node_type.value}"],
                    modified
                )


def hash_tree(root: ASTNode, algorithm: str = "sha256") -> ASTNode:
    """
    Convenience function to hash an entire AST tree.

    Args:
        root: Root node of the tree
        algorithm: Hash algorithm to use

    Returns:
        The root node (with all hashes computed)
    """
    hasher = NodeHasher(algorithm=algorithm)
    hasher.hash_node(root, recursive=True)
    return root
