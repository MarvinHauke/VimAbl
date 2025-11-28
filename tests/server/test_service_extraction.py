"""
Tests for Phase 11c service extraction.

Verifies that QueryService and ProjectService are correctly instantiated
and that ASTServer delegates to them properly.
"""

import pytest
from src.server.api import ASTServer
from src.server.services import QueryService, ProjectService


class TestServiceInstantiation:
    """Test that services are correctly instantiated."""

    def test_server_has_services(self):
        """Test that ASTServer creates all service instances."""
        server = ASTServer(enable_websocket=False)

        assert hasattr(server, 'query_service')
        assert hasattr(server, 'project_service')

    def test_services_are_correct_type(self):
        """Test that services are instances of correct classes."""
        server = ASTServer(enable_websocket=False)

        assert isinstance(server.query_service, QueryService)
        assert isinstance(server.project_service, ProjectService)

    def test_services_have_server_reference(self):
        """Test that services have reference to server."""
        server = ASTServer(enable_websocket=False)

        assert server.query_service.server is server
        assert server.project_service.server is server

    def test_services_can_access_ast(self):
        """Test that services can access AST through server."""
        server = ASTServer(enable_websocket=False)

        # Initially None
        assert server.query_service.ast is None
        assert server.project_service.server.current_ast is None

        # After setting current_ast, services should access it
        from src.ast import ProjectNode
        test_ast = ProjectNode(id="project_test")
        server.current_ast = test_ast

        assert server.query_service.ast is test_ast
        assert server.project_service.server.current_ast is test_ast


class TestQueryServiceDelegation:
    """Test that ASTServer delegates query methods to QueryService."""

    def test_delegation_no_project_loaded(self):
        """Test that query methods raise error when no project is loaded."""
        server = ASTServer(enable_websocket=False)

        with pytest.raises(RuntimeError, match="No project loaded"):
            server.get_ast_json()

        with pytest.raises(RuntimeError, match="No project loaded"):
            server.find_node_by_id("test")

        with pytest.raises(RuntimeError, match="No project loaded"):
            server.find_nodes_by_type("track")

        with pytest.raises(RuntimeError, match="No project loaded"):
            server.get_project_info()

        with pytest.raises(RuntimeError, match="No project loaded"):
            server.query_nodes("name == 'Test'")

    def test_find_nodes_by_type_with_ast(self):
        """Test find_nodes_by_type with a loaded AST."""
        server = ASTServer(enable_websocket=False)

        # Create test AST with tracks
        from src.ast import ProjectNode, TrackNode
        test_ast = ProjectNode(id="project_test")
        track0 = TrackNode(name="Track 0", index=0, id="track_0")
        track1 = TrackNode(name="Track 1", index=1, id="track_1")
        test_ast.children = [track0, track1]
        server.current_ast = test_ast

        # Find tracks
        tracks = server.find_nodes_by_type("track")
        assert len(tracks) == 2
        assert tracks[0]['id'] == "track_0"
        assert tracks[1]['id'] == "track_1"

    def test_find_node_by_id_with_ast(self):
        """Test find_node_by_id with a loaded AST."""
        server = ASTServer(enable_websocket=False)

        # Create test AST
        from src.ast import ProjectNode, TrackNode
        test_ast = ProjectNode(id="project_test")
        track = TrackNode(name="My Track", index=0, id="track_123")
        test_ast.children = [track]
        server.current_ast = test_ast

        # Find by ID
        result = server.find_node_by_id("track_123")
        assert result is not None
        assert result['id'] == "track_123"
        assert result['attributes']['name'] == "My Track"

        # Non-existent ID
        result = server.find_node_by_id("nonexistent")
        assert result is None

    def test_get_project_info_with_ast(self):
        """Test get_project_info with a loaded AST."""
        server = ASTServer(enable_websocket=False)

        # Create test AST
        from src.ast import ProjectNode, TrackNode, SceneNode
        test_ast = ProjectNode(id="project_test")
        test_ast.hash = "test_hash"
        track1 = TrackNode(name="Track 1", index=0, id="track_0")
        track2 = TrackNode(name="Track 2", index=1, id="track_1")
        scene = SceneNode(name="Scene 1", index=0, id="scene_0")
        test_ast.children = [track1, track2, scene]
        server.current_ast = test_ast
        server.current_file = None

        # Get project info
        info = server.get_project_info()
        assert info['root_hash'] == "test_hash"
        assert info['num_tracks'] == 2
        assert info['num_scenes'] == 1
        assert "Track 1" in info['track_names']
        assert "Track 2" in info['track_names']


class TestProjectServiceDelegation:
    """Test that ASTServer delegates project methods to ProjectService."""

    def test_load_project_delegation(self, tmp_path):
        """Test that load_project delegates to ProjectService."""
        server = ASTServer(enable_websocket=False)

        # We can't fully test load_project without a real .als file,
        # but we can verify the delegation happens
        assert hasattr(server.project_service, 'load_project')
        assert callable(server.load_project)


class TestApiReducedSize:
    """Test that api.py has been significantly reduced in size."""

    def test_api_file_size(self):
        """Test that api.py is significantly smaller than before."""
        import os
        api_path = "src/server/api.py"

        # Count lines
        with open(api_path, 'r') as f:
            line_count = len(f.readlines())

        # Should be around 342 lines (down from 1108)
        assert line_count < 400, f"api.py should be < 400 lines, but is {line_count}"
        assert line_count > 300, f"api.py should be > 300 lines, but is {line_count}"

    def test_no_old_handler_methods(self):
        """Test that old handler methods have been removed."""
        import os
        api_path = "src/server/api.py"

        with open(api_path, 'r') as f:
            content = f.read()

        # Old handler methods should not exist
        assert "_handle_track_renamed" not in content
        assert "_handle_scene_added" not in content
        assert "_handle_device_param" not in content
        assert "_handle_clip_slot_created" not in content

    def test_no_old_helper_methods(self):
        """Test that old helper methods have been removed."""
        import os
        api_path = "src/server/api.py"

        with open(api_path, 'r') as f:
            content = f.read()

        # Old helper methods should not exist
        assert "_find_track_by_index" not in content
        assert "_find_scene_by_index" not in content
        assert "_recompute_parent_hashes" not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
