import pytest
from unittest.mock import MagicMock, patch
from src.server.services.query_service import QueryService
from src.ast import ProjectNode, TrackNode, NodeType

class MockServer:
    def __init__(self):
        self.current_ast = ProjectNode()
        self.current_ast.id = "project-root"
        self.current_ast.hash = "hash123"
        self.current_file = "test.als"

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def service(server):
    return QueryService(server)

def test_get_ast_json_success(service, server):
    """
    Test get_ast_json returns JSON string.
    """
    json_str = service.get_ast_json()
    assert isinstance(json_str, str)
    assert '"node_type": "project"' in json_str

def test_get_ast_json_no_project(service, server):
    """
    Test get_ast_json raises RuntimeError if no project loaded.
    """
    server.current_ast = None
    with pytest.raises(RuntimeError, match="No project loaded"):
        service.get_ast_json()

def test_find_node_by_id_success(service, server):
    """
    Test find_node_by_id returns serialized node.
    """
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.id = "track-0"
    server.current_ast.add_child(track_node)

    result = service.find_node_by_id("track-0")
    assert result is not None
    assert result["id"] == "track-0"
    assert result["node_type"] == "track"

def test_find_node_by_id_not_found(service, server):
    """
    Test find_node_by_id returns None if not found.
    """
    result = service.find_node_by_id("non-existent")
    assert result is None

def test_find_nodes_by_type_success(service, server):
    """
    Test find_nodes_by_type returns list of nodes.
    """
    track1 = TrackNode(name="T1", index=0)
    track2 = TrackNode(name="T2", index=1)
    server.current_ast.add_child(track1)
    server.current_ast.add_child(track2)

    result = service.find_nodes_by_type("track")
    assert len(result) == 2
    assert result[0]["attributes"]["name"] == "T1"
    assert result[1]["attributes"]["name"] == "T2"

def test_find_nodes_by_type_invalid_type(service, server):
    """
    Test find_nodes_by_type returns empty list for invalid type.
    """
    result = service.find_nodes_by_type("invalid_type")
    assert result == []

def test_query_nodes_simple_predicate(service, server):
    """
    Test query_nodes with simple equality predicate.
    """
    track1 = TrackNode(name="Target", index=0)
    track2 = TrackNode(name="Other", index=1)
    server.current_ast.add_child(track1)
    server.current_ast.add_child(track2)

    result = service.query_nodes("name == Target")
    assert len(result) == 1
    assert result[0]["attributes"]["name"] == "Target"

def test_get_project_info_success(service, server):
    """
    Test get_project_info returns stats.
    """
    track = TrackNode(name="Audio 1", index=0)
    server.current_ast.add_child(track)

    stats = service.get_project_info()
    assert stats["file"] == "test.als"
    assert stats["root_hash"] == "hash123"
    assert stats["num_tracks"] == 1
    assert stats["track_names"] == ["Audio 1"]

def test_diff_with_file_success(service, server):
    """
    Test diff_with_file computes diff.
    """
    # Mock loading other file
    mock_other_ast = ProjectNode()
    mock_other_ast.id = "project-root" # Same ID to allow diff
    
    with patch("src.server.services.query_service.load_ableton_xml"), \
         patch("src.server.services.query_service.build_ast"), \
         patch("src.server.services.query_service.ASTBuilder.build_node_tree", return_value=mock_other_ast), \
         patch("src.server.services.query_service.hash_tree"):
        
        changes = service.diff_with_file("other.als")
        assert isinstance(changes, list)
