"""
Visitor pattern implementation for AST traversal, diffing, and serialization.

This module provides:
- Generic visitor pattern for AST traversal
- Serialization to JSON/dict
- Diff computation between two AST trees
- Pretty printing for debugging
"""

from typing import Any, Dict, List, Optional, Callable
from .node import ASTNode, NodeType
import json


class ASTVisitor:
    """
    Base visitor class for traversing AST nodes.

    Subclass this and override visit_* methods to implement custom behavior.
    """

    def visit(self, node: ASTNode) -> Any:
        """
        Visit a node and dispatch to the appropriate visit_* method.

        This implements double dispatch by calling visit_{node_type.value}.
        """
        method_name = f"visit_{node.node_type.value}"
        visitor_method = getattr(self, method_name, self.generic_visit)
        return visitor_method(node)

    def generic_visit(self, node: ASTNode) -> Any:
        """Default visit method that traverses children."""
        results = []
        for child in node.children:
            results.append(self.visit(child))
        return results

    def traverse(self, node: ASTNode, pre_order: bool = True) -> List[ASTNode]:
        """
        Traverse the tree and collect all nodes.

        Args:
            node: Root node to start traversal
            pre_order: If True, use pre-order traversal; otherwise post-order

        Returns:
            List of all nodes in traversal order
        """
        nodes = []
        if pre_order:
            nodes.append(node)
        for child in node.children:
            nodes.extend(self.traverse(child, pre_order))
        if not pre_order:
            nodes.append(node)
        return nodes


class SerializationVisitor(ASTVisitor):
    """Visitor that serializes AST to JSON-compatible dict structure."""

    def __init__(self, include_hash: bool = True, include_parent_ref: bool = False):
        self.include_hash = include_hash
        self.include_parent_ref = include_parent_ref

    def generic_visit(self, node: ASTNode) -> Dict[str, Any]:
        """Serialize a node to a dictionary."""
        result = {
            "node_type": node.node_type.value,
            "id": node.id,
            "attributes": node.attributes.copy(),
            "children": [self.visit(child) for child in node.children],
        }

        if self.include_hash and node.hash:
            result["hash"] = node.hash

        if self.include_parent_ref and node.parent:
            result["parent_id"] = node.parent.id

        return result

    def to_json(self, node: ASTNode, indent: int = 2) -> str:
        """Serialize AST to JSON string."""
        return json.dumps(self.visit(node), indent=indent)


class DiffVisitor(ASTVisitor):
    """
    Visitor that computes differences between two AST trees.

    Returns a list of changes: additions, deletions, and modifications.
    """

    def __init__(self):
        self.changes = []

    def diff(self, old_tree: ASTNode, new_tree: ASTNode) -> List[Dict[str, Any]]:
        """
        Compute diff between two AST trees.

        Returns:
            List of change records with format:
            {
                "type": "added" | "removed" | "modified",
                "path": ["project", "track_0", ...],
                "node_type": "track",
                "old_value": {...},
                "new_value": {...}
            }
        """
        self.changes = []
        self._diff_nodes(old_tree, new_tree, [])
        return self.changes

    def _diff_nodes(self, old: Optional[ASTNode], new: Optional[ASTNode], path: List[str]) -> None:
        """Recursively compare two nodes and their children."""
        # Node removed
        if old is not None and new is None:
            self.changes.append({
                "type": "removed",
                "path": path,
                "node_type": old.node_type.value,
                "old_value": self._node_to_dict(old),
                "new_value": None,
            })
            return

        # Node added
        if old is None and new is not None:
            self.changes.append({
                "type": "added",
                "path": path,
                "node_type": new.node_type.value,
                "old_value": None,
                "new_value": self._node_to_dict(new),
            })
            return

        # Both exist - check for modifications
        if old is not None and new is not None:
            # Check if attributes changed
            if old.attributes != new.attributes:
                self.changes.append({
                    "type": "modified",
                    "path": path,
                    "node_type": old.node_type.value,
                    "old_value": old.attributes.copy(),
                    "new_value": new.attributes.copy(),
                })

            # Recursively diff children
            # Match children by ID if available, otherwise by index
            old_children_by_id = {c.id: c for c in old.children if c.id}
            new_children_by_id = {c.id: c for c in new.children if c.id}

            # Check for added/removed children with IDs
            all_ids = set(old_children_by_id.keys()) | set(new_children_by_id.keys())
            for child_id in all_ids:
                old_child = old_children_by_id.get(child_id)
                new_child = new_children_by_id.get(child_id)
                child_path = path + [child_id]
                self._diff_nodes(old_child, new_child, child_path)

            # For children without IDs, compare by index
            old_no_id = [c for c in old.children if not c.id]
            new_no_id = [c for c in new.children if not c.id]
            max_len = max(len(old_no_id), len(new_no_id))

            for i in range(max_len):
                old_child = old_no_id[i] if i < len(old_no_id) else None
                new_child = new_no_id[i] if i < len(new_no_id) else None
                child_path = path + [f"index_{i}"]
                self._diff_nodes(old_child, new_child, child_path)

    def _node_to_dict(self, node: ASTNode) -> Dict[str, Any]:
        """Convert node to a simple dict representation."""
        return {
            "node_type": node.node_type.value,
            "id": node.id,
            "attributes": node.attributes.copy(),
        }


class PrettyPrintVisitor(ASTVisitor):
    """Visitor that creates a human-readable string representation of the AST."""

    def __init__(self, indent: int = 2):
        self.indent = indent
        self.current_depth = 0

    def generic_visit(self, node: ASTNode) -> str:
        """Create indented string representation."""
        indent_str = " " * (self.current_depth * self.indent)
        lines = [f"{indent_str}{node.node_type.value}"]

        if node.id:
            lines[0] += f" (id: {node.id})"

        # Add key attributes
        if node.attributes:
            for key, value in node.attributes.items():
                if value is not None and key not in ['children']:
                    lines.append(f"{indent_str}  {key}: {value}")

        # Visit children
        self.current_depth += 1
        for child in node.children:
            lines.append(self.visit(child))
        self.current_depth -= 1

        return "\n".join(lines)

    def print(self, node: ASTNode) -> str:
        """Generate pretty-printed string of the AST."""
        self.current_depth = 0
        return self.visit(node)


class SearchVisitor(ASTVisitor):
    """Visitor for searching nodes by various criteria."""

    def find_by_id(self, root: ASTNode, node_id: str) -> Optional[ASTNode]:
        """Find a node by its ID."""
        if root.id == node_id:
            return root
        for child in root.children:
            result = self.find_by_id(child, node_id)
            if result:
                return result
        return None

    def find_by_type(self, root: ASTNode, node_type: NodeType) -> List[ASTNode]:
        """Find all nodes of a specific type."""
        results = []
        if root.node_type == node_type:
            results.append(root)
        for child in root.children:
            results.extend(self.find_by_type(child, node_type))
        return results

    def find_by_predicate(self, root: ASTNode, predicate: Callable[[ASTNode], bool]) -> List[ASTNode]:
        """Find all nodes matching a predicate function."""
        results = []
        if predicate(root):
            results.append(root)
        for child in root.children:
            results.extend(self.find_by_predicate(child, predicate))
        return results
