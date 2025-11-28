"""
Tests for AST caching functionality (Phase 11d).

Verifies that:
1. ASTCache correctly stores and retrieves track/scene lookups
2. Version-based invalidation works correctly
3. Cache statistics are tracked properly
4. LRU eviction works when capacity is reached
5. ASTNavigator uses cache when provided
"""

import pytest
from src.server.api import ASTServer
from src.server.utils import ASTCache
from src.server.ast_helpers import ASTNavigator
from src.ast import ProjectNode, TrackNode, SceneNode, NodeType


class TestASTCache:
    """Test the ASTCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with default and custom settings."""
        cache1 = ASTCache()
        assert cache1.enabled is True
        assert cache1.capacity == 256

        cache2 = ASTCache(enabled=False, capacity=128)
        assert cache2.enabled is False
        assert cache2.capacity == 128

    def test_track_by_index_caching(self):
        """Test caching of track lookups by index."""
        cache = ASTCache()

        # Create a test track
        track = TrackNode(name="Test Track", index=0, id="track_0")

        # Initially should be a miss
        result = cache.get_track_by_index(0, ast_version="v1")
        assert result is None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

        # Cache the track
        cache.put_track_by_index(0, track, ast_version="v1")

        # Now should be a hit
        result = cache.get_track_by_index(0, ast_version="v1")
        assert result is track
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_scene_by_index_caching(self):
        """Test caching of scene lookups by index."""
        cache = ASTCache()

        # Create a test scene
        scene = SceneNode(name="Test Scene", index=0, id="scene_0")

        # Initially should be a miss
        result = cache.get_scene_by_index(0, ast_version="v1")
        assert result is None

        # Cache the scene
        cache.put_scene_by_index(0, scene, ast_version="v1")

        # Now should be a hit
        result = cache.get_scene_by_index(0, ast_version="v1")
        assert result is scene

    def test_all_tracks_caching(self):
        """Test caching of all tracks list."""
        cache = ASTCache()

        tracks = [
            TrackNode(name="Track 0", index=0, id="track_0"),
            TrackNode(name="Track 1", index=1, id="track_1"),
        ]

        # Initially should be a miss
        result = cache.get_all_tracks(ast_version="v1")
        assert result is None

        # Cache the tracks
        cache.put_all_tracks(tracks, ast_version="v1")

        # Now should be a hit
        result = cache.get_all_tracks(ast_version="v1")
        assert result == tracks
        assert len(result) == 2

    def test_all_scenes_caching(self):
        """Test caching of all scenes list."""
        cache = ASTCache()

        scenes = [
            SceneNode(name="Scene 0", index=0, id="scene_0"),
            SceneNode(name="Scene 1", index=1, id="scene_1"),
        ]

        # Cache the scenes
        cache.put_all_scenes(scenes, ast_version="v1")

        # Should be a hit
        result = cache.get_all_scenes(ast_version="v1")
        assert result == scenes

    def test_version_based_invalidation(self):
        """Test that cache invalidates when AST version changes."""
        cache = ASTCache()

        track = TrackNode(name="Test Track", index=0, id="track_0")

        # Cache with version v1 (triggers first invalidation since version is None)
        cache.put_track_by_index(0, track, ast_version="v1")
        result = cache.get_track_by_index(0, ast_version="v1")
        assert result is track

        # Reset stats after initial setup
        initial_invalidations = cache.stats.invalidations
        cache.stats.reset()

        # Change version - should invalidate and return None
        result = cache.get_track_by_index(0, ast_version="v2")
        assert result is None
        assert cache.stats.invalidations == 1  # One invalidation for version change

    def test_disabled_cache(self):
        """Test that disabled cache returns None for all operations."""
        cache = ASTCache(enabled=False)

        track = TrackNode(name="Test Track", index=0, id="track_0")

        # Put should be no-op
        cache.put_track_by_index(0, track, ast_version="v1")

        # Get should always return None
        result = cache.get_track_by_index(0, ast_version="v1")
        assert result is None

        # Stats should not increment
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = ASTCache()

        track = TrackNode(name="Test Track", index=0, id="track_0")

        # One miss
        cache.get_track_by_index(0, ast_version="v1")

        # Cache it
        cache.put_track_by_index(0, track, ast_version="v1")

        # Two hits
        cache.get_track_by_index(0, ast_version="v1")
        cache.get_track_by_index(0, ast_version="v1")

        stats = cache.get_stats()
        assert stats['statistics']['hits'] == 2
        assert stats['statistics']['misses'] == 1
        assert stats['statistics']['total_requests'] == 3
        assert stats['statistics']['hit_rate'] == 2/3

    def test_lru_eviction(self):
        """Test LRU eviction when capacity is reached."""
        cache = ASTCache(capacity=2)

        # Cache 3 tracks (capacity is 2)
        for i in range(3):
            track = TrackNode(name=f"Track {i}", index=i, id=f"track_{i}")
            cache.put_track_by_index(i, track, ast_version="v1")

        # First track should have been evicted (LRU)
        result = cache.get_track_by_index(0, ast_version="v1")
        assert result is None  # Evicted

        # Second and third should still be there
        result = cache.get_track_by_index(1, ast_version="v1")
        assert result is not None

        result = cache.get_track_by_index(2, ast_version="v1")
        assert result is not None


class TestASTNavigatorWithCache:
    """Test ASTNavigator integration with caching."""

    def setup_method(self):
        """Set up test AST."""
        self.root = ProjectNode(id="project_test")
        self.root.hash = "test_hash_v1"

        # Add tracks
        self.tracks = [
            TrackNode(name="Track 0", index=0, id="track_0"),
            TrackNode(name="Track 1", index=1, id="track_1"),
            TrackNode(name="Track 2", index=2, id="track_2"),
        ]

        # Add scenes
        self.scenes = [
            SceneNode(name="Scene 0", index=0, id="scene_0"),
            SceneNode(name="Scene 1", index=1, id="scene_1"),
        ]

        self.root.children = self.tracks + self.scenes

    def test_find_track_by_index_with_cache(self):
        """Test find_track_by_index uses cache correctly."""
        cache = ASTCache()

        # First call - cache miss
        track = ASTNavigator.find_track_by_index(self.root, 0, cache=cache)
        assert track is not None
        assert track.attributes['name'] == "Track 0"
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

        # Second call - cache hit
        track = ASTNavigator.find_track_by_index(self.root, 0, cache=cache)
        assert track is not None
        assert track.attributes['name'] == "Track 0"
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_find_scene_by_index_with_cache(self):
        """Test find_scene_by_index uses cache correctly."""
        cache = ASTCache()

        # First call - cache miss
        scene = ASTNavigator.find_scene_by_index(self.root, 0, cache=cache)
        assert scene is not None
        assert scene.attributes['name'] == "Scene 0"
        assert cache.stats.misses == 1

        # Second call - cache hit
        scene = ASTNavigator.find_scene_by_index(self.root, 0, cache=cache)
        assert scene is not None
        assert cache.stats.hits == 1

    def test_get_tracks_with_cache(self):
        """Test get_tracks uses cache correctly."""
        cache = ASTCache()

        # First call - cache miss
        tracks = ASTNavigator.get_tracks(self.root, cache=cache)
        assert len(tracks) == 3
        assert cache.stats.misses == 1

        # Second call - cache hit
        tracks = ASTNavigator.get_tracks(self.root, cache=cache)
        assert len(tracks) == 3
        assert cache.stats.hits == 1

    def test_get_scenes_with_cache(self):
        """Test get_scenes uses cache correctly."""
        cache = ASTCache()

        # First call - cache miss
        scenes = ASTNavigator.get_scenes(self.root, cache=cache)
        assert len(scenes) == 2
        assert cache.stats.misses == 1

        # Second call - cache hit
        scenes = ASTNavigator.get_scenes(self.root, cache=cache)
        assert len(scenes) == 2
        assert cache.stats.hits == 1

    def test_navigator_without_cache(self):
        """Test that ASTNavigator works without cache (backward compatibility)."""
        # Should work without passing cache parameter
        track = ASTNavigator.find_track_by_index(self.root, 0)
        assert track is not None
        assert track.attributes['name'] == "Track 0"

        scene = ASTNavigator.find_scene_by_index(self.root, 0)
        assert scene is not None
        assert scene.attributes['name'] == "Scene 0"

        tracks = ASTNavigator.get_tracks(self.root)
        assert len(tracks) == 3

        scenes = ASTNavigator.get_scenes(self.root)
        assert len(scenes) == 2


class TestASTServerCaching:
    """Test caching integration in ASTServer."""

    def test_server_has_cache(self):
        """Test that ASTServer creates cache instance."""
        server = ASTServer(enable_websocket=False)

        assert hasattr(server, 'cache')
        assert isinstance(server.cache, ASTCache)
        assert server.cache.enabled is True

    def test_server_cache_configuration(self):
        """Test cache configuration options."""
        # Disabled cache
        server1 = ASTServer(enable_websocket=False, enable_cache=False)
        assert server1.cache.enabled is False

        # Custom capacity
        server2 = ASTServer(enable_websocket=False, cache_capacity=128)
        assert server2.cache.capacity == 128

    def test_server_cache_stats(self):
        """Test server cache statistics endpoint."""
        server = ASTServer(enable_websocket=False)

        stats = server.get_cache_stats()
        assert 'enabled' in stats
        assert 'capacity' in stats
        assert 'statistics' in stats
        assert stats['enabled'] is True
        assert stats['capacity'] == 256

    def test_cache_invalidates_on_ast_change(self):
        """Test that cache invalidates when AST changes."""
        server = ASTServer(enable_websocket=False)

        # Create initial AST
        root1 = ProjectNode(id="project_1")
        root1.hash = "hash_v1"
        track1 = TrackNode(name="Track 1", index=0, id="track_0")
        root1.children = [track1]
        server.current_ast = root1

        # Use cache
        track = ASTNavigator.find_track_by_index(server.current_ast, 0, cache=server.cache)
        assert track is not None

        # Cache should have 1 hit after second call
        track = ASTNavigator.find_track_by_index(server.current_ast, 0, cache=server.cache)
        stats = server.get_cache_stats()
        assert stats['statistics']['hits'] == 1

        # Reset stats after setup
        server.cache.stats.reset()

        # Change AST (different hash)
        root2 = ProjectNode(id="project_2")
        root2.hash = "hash_v2"
        track2 = TrackNode(name="Track 2", index=0, id="track_0_new")
        root2.children = [track2]
        server.current_ast = root2

        # Cache should invalidate - this will be a miss
        track = ASTNavigator.find_track_by_index(server.current_ast, 0, cache=server.cache)
        stats = server.get_cache_stats()
        # After version change, we should have 1 invalidation
        assert stats['statistics']['invalidations'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
