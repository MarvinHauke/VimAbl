"""
Tests for Phase 11b handler separation.

Verifies that specialized handler classes are correctly instantiated
and event routing works as expected.
"""

import pytest
from src.server.api import ASTServer
from src.server.handlers import (
    TrackEventHandler,
    SceneEventHandler,
    DeviceEventHandler,
    ClipSlotEventHandler,
    TransportEventHandler,
)


class TestHandlerInstantiation:
    """Test that handlers are correctly instantiated."""

    def test_server_has_handlers(self):
        """Test that ASTServer creates all handler instances."""
        server = ASTServer(enable_websocket=False)

        assert hasattr(server, 'track_handler')
        assert hasattr(server, 'scene_handler')
        assert hasattr(server, 'device_handler')
        assert hasattr(server, 'clip_slot_handler')
        assert hasattr(server, 'transport_handler')

    def test_handlers_are_correct_type(self):
        """Test that handlers are instances of correct classes."""
        server = ASTServer(enable_websocket=False)

        assert isinstance(server.track_handler, TrackEventHandler)
        assert isinstance(server.scene_handler, SceneEventHandler)
        assert isinstance(server.device_handler, DeviceEventHandler)
        assert isinstance(server.clip_slot_handler, ClipSlotEventHandler)
        assert isinstance(server.transport_handler, TransportEventHandler)

    def test_handlers_have_server_reference(self):
        """Test that handlers have reference to server."""
        server = ASTServer(enable_websocket=False)

        assert server.track_handler.server is server
        assert server.scene_handler.server is server
        assert server.device_handler.server is server
        assert server.clip_slot_handler.server is server
        assert server.transport_handler.server is server

    def test_handlers_have_ast_reference(self):
        """Test that handlers can access AST through server."""
        server = ASTServer(enable_websocket=False)

        # Initially None
        assert server.track_handler.ast is None
        assert server.scene_handler.ast is None

        # After setting current_ast, handlers should access it
        from src.ast import ProjectNode
        test_ast = ProjectNode(id="project_test")
        test_ast.attributes['name'] = "Test Project"
        server.current_ast = test_ast

        assert server.track_handler.ast is test_ast
        assert server.scene_handler.ast is test_ast


class TestEventHandlerRegistry:
    """Test event handler registry routing."""

    def test_registry_maps_to_handlers(self):
        """Test that registry maps events to handler methods."""
        server = ASTServer(enable_websocket=False)
        registry = server._event_handlers

        # Track events
        assert "/live/track/renamed" in registry
        assert registry["/live/track/renamed"] == server.track_handler.handle_track_renamed

        # Device events
        assert "/live/device/added" in registry
        assert registry["/live/device/added"] == server.device_handler.handle_device_added

        # Scene events
        assert "/live/scene/added" in registry
        assert registry["/live/scene/added"] == server.scene_handler.handle_scene_added

        # Clip slot events
        assert "/live/clip_slot/created" in registry
        assert registry["/live/clip_slot/created"] == server.clip_slot_handler.handle_clip_slot_created

    def test_track_state_lambdas(self):
        """Test that track state events use lambdas correctly."""
        server = ASTServer(enable_websocket=False)
        registry = server._event_handlers

        # Track state events should be in registry
        assert "/live/track/mute" in registry
        assert "/live/track/arm" in registry
        assert "/live/track/volume" in registry

        # They should be callables (lambdas)
        assert callable(registry["/live/track/mute"])
        assert callable(registry["/live/track/arm"])
        assert callable(registry["/live/track/volume"])


class TestHandlerHelperMethods:
    """Test helper methods in handlers."""

    def test_find_track_helper(self):
        """Test _find_track helper method."""
        server = ASTServer(enable_websocket=False)

        # Create test AST with tracks
        from src.ast import ProjectNode, TrackNode
        test_ast = ProjectNode(id="project_test")
        track0 = TrackNode(name="Track 0", index=0, id="track_0")
        track1 = TrackNode(name="Track 1", index=1, id="track_1")
        test_ast.children = [track0, track1]
        server.current_ast = test_ast

        # Test finding tracks
        found_track = server.track_handler._find_track(0)
        assert found_track is not None
        assert found_track.id == "track_0"

        found_track = server.track_handler._find_track(1)
        assert found_track is not None
        assert found_track.id == "track_1"

        # Non-existent track
        found_track = server.track_handler._find_track(99)
        assert found_track is None

    def test_broadcast_helpers(self):
        """Test broadcast helper methods."""
        server = ASTServer(enable_websocket=False)

        # Handlers should have broadcast helpers
        assert hasattr(server.track_handler, '_broadcast_if_running')
        assert hasattr(server.track_handler, '_broadcast_error_if_running')
        assert hasattr(server.scene_handler, '_broadcast_if_running')
        assert hasattr(server.device_handler, '_broadcast_if_running')


class TestDebouncer:
    """Test that handlers can access debouncer."""

    def test_device_handler_can_access_debouncer(self):
        """Test that device handler can access debouncer for param changes."""
        server = ASTServer(enable_websocket=False)

        # Device handler should be able to access server.debouncer
        assert hasattr(server, 'debouncer')
        assert server.device_handler.server.debouncer is server.debouncer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
