"""Serializers for converting AST nodes to JSON-serializable dictionaries."""

import json
from typing import Any, Dict, List, Optional
from ..ast.node import (
    ASTNode,
    ProjectNode,
    TrackNode,
    DeviceNode,
    ClipNode,
    SceneNode,
    MixerNode,
    FileRefNode,
)


class ASTSerializer:
    """Serializes AST nodes to JSON-compatible dictionaries."""

    @staticmethod
    def serialize_node(node: ASTNode, include_children: bool = True, depth: int = -1) -> Dict[str, Any]:
        """
        Serialize an AST node to a JSON-compatible dictionary.

        Args:
            node: The AST node to serialize
            include_children: Whether to include child nodes
            depth: Maximum depth to serialize (-1 for unlimited)

        Returns:
            Dictionary representation of the node
        """
        # Convert NodeType enum to string
        node_type_str = node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type)

        result: Dict[str, Any] = {
            'node_type': node_type_str,
            'id': node.id,
            'hash': node.hash,
            'attributes': node.attributes.copy(),
        }

        # Add children if requested and depth allows
        if include_children and depth != 0 and node.children:
            result['children'] = [
                ASTSerializer.serialize_node(child, include_children, depth - 1)
                for child in node.children
            ]
        elif node.children:
            # Just include child count if not including children
            result['child_count'] = len(node.children)

        return result

    @staticmethod
    def serialize_diff(diff_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize a diff result from DiffVisitor.

        Args:
            diff_result: The diff result dictionary

        Returns:
            JSON-compatible diff representation
        """
        return {
            'changes': diff_result.get('changes', []),
            'added': diff_result.get('added', []),
            'removed': diff_result.get('removed', []),
            'modified': diff_result.get('modified', []),
            'unchanged': diff_result.get('unchanged', []),
        }

    @staticmethod
    def to_json(data: Dict[str, Any], pretty: bool = False) -> str:
        """
        Convert dictionary to JSON string.

        Args:
            data: Dictionary to serialize
            pretty: Whether to use pretty formatting

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)


# Convenience function
def serialize_node(node: ASTNode, include_children: bool = True, depth: int = -1) -> Dict[str, Any]:
    """
    Convenience function to serialize a node.

    Args:
        node: The AST node to serialize
        include_children: Whether to include child nodes
        depth: Maximum depth to serialize (-1 for unlimited)

    Returns:
        Dictionary representation of the node
    """
    return ASTSerializer.serialize_node(node, include_children, depth)


def create_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a WebSocket message with a type and payload.

    Args:
        msg_type: Message type (FULL_AST, DIFF_UPDATE, ERROR, ACK, etc.)
        payload: Message payload

    Returns:
        Message dictionary
    """
    return {
        'type': msg_type,
        'payload': payload,
    }


def create_full_ast_message(root: ASTNode, project_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a FULL_AST message.

    Args:
        root: Root AST node
        project_path: Optional path to the project file

    Returns:
        Message dictionary
    """
    payload = {
        'ast': serialize_node(root),
    }

    if project_path:
        payload['project_path'] = project_path

    return create_message('FULL_AST', payload)


def create_diff_message(diff_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a DIFF_UPDATE message.

    Args:
        diff_result: Diff result from DiffVisitor

    Returns:
        Message dictionary
    """
    return create_message('DIFF_UPDATE', {
        'diff': ASTSerializer.serialize_diff(diff_result),
    })


def create_error_message(error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an ERROR message.

    Args:
        error: Error message
        details: Optional error details

    Returns:
        Message dictionary
    """
    payload = {'error': error}
    if details:
        payload['details'] = details
    return create_message('ERROR', payload)


def create_ack_message(request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an ACK message.

    Args:
        request_id: Optional request ID being acknowledged

    Returns:
        Message dictionary
    """
    payload = {'status': 'ok'}
    if request_id:
        payload['request_id'] = request_id
    return create_message('ACK', payload)
