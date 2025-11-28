"""
AST caching system for performance optimization.

Provides LRU caching for frequently accessed AST nodes with version-based
invalidation to ensure consistency.
"""

import logging
from functools import lru_cache
from typing import Optional, Dict, Any, List, Callable, TypeVar, Generic
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LRUCache(Generic[T]):
    """
    Generic LRU (Least Recently Used) cache implementation.

    Automatically evicts least recently accessed items when capacity is reached.
    """

    def __init__(self, capacity: int = 128):
        """
        Initialize LRU cache.

        Args:
            capacity: Maximum number of items to cache (default: 128)
        """
        self.capacity = capacity
        self.cache: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key not in self.cache:
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: T) -> None:
        """
        Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing and move to end
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            # Remove least recently used (first item)
            self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


class CacheStats:
    """Statistics for cache performance monitoring."""

    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.invalidations: int = 0
        self.evictions: int = 0

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    def record_invalidation(self) -> None:
        """Record a cache invalidation."""
        self.invalidations += 1

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1

    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0

    def to_dict(self) -> Dict[str, Any]:
        """Export statistics as dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'invalidations': self.invalidations,
            'evictions': self.evictions,
            'total_requests': self.total_requests,
            'hit_rate': self.hit_rate,
        }


class ASTCache:
    """
    Cache for AST node lookups with version-based invalidation.

    Caches frequently accessed nodes (tracks by index, scenes by index, etc.)
    and invalidates automatically when the AST version changes.

    Usage:
        cache = ASTCache(enabled=True, capacity=256)

        # Cache will automatically invalidate when ast_version changes
        track = cache.get_track_by_index(0, ast_version="abc123")
        if track is None:
            track = compute_track(0)
            cache.put_track_by_index(0, track, ast_version="abc123")
    """

    def __init__(self, enabled: bool = True, capacity: int = 256):
        """
        Initialize AST cache.

        Args:
            enabled: Whether caching is enabled (default: True)
            capacity: Maximum number of items per cache type (default: 256)
        """
        self.enabled = enabled
        self.capacity = capacity

        # Current AST version (hash) - used for invalidation
        self._current_version: Optional[str] = None

        # Separate caches for different lookup types
        self._track_by_index: LRUCache = LRUCache(capacity)
        self._scene_by_index: LRUCache = LRUCache(capacity)
        self._tracks_all: Optional[Any] = None
        self._scenes_all: Optional[Any] = None

        # Statistics
        self.stats = CacheStats()

        logger.debug(f"ASTCache initialized: enabled={enabled}, capacity={capacity}")

    def set_version(self, version: str) -> None:
        """
        Set the current AST version.

        If version changes, all caches are invalidated.

        Args:
            version: AST version identifier (typically the root hash)
        """
        if self._current_version != version:
            logger.debug(f"AST version changed: {self._current_version} -> {version}")
            self.invalidate_all()
            self._current_version = version

    def invalidate_all(self) -> None:
        """Invalidate all cached data."""
        if not self.enabled:
            return

        self._track_by_index.clear()
        self._scene_by_index.clear()
        self._tracks_all = None
        self._scenes_all = None
        self.stats.record_invalidation()

        logger.debug("All caches invalidated")

    # Track lookups

    def get_track_by_index(self, index: int, ast_version: Optional[str] = None) -> Optional[Any]:
        """
        Get cached track by index.

        Args:
            index: Track index
            ast_version: Optional AST version for automatic invalidation

        Returns:
            Cached TrackNode or None if not found
        """
        if not self.enabled:
            return None

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        key = f"track_{index}"
        result = self._track_by_index.get(key)

        if result is not None:
            self.stats.record_hit()
            logger.debug(f"Cache HIT: {key}")
        else:
            self.stats.record_miss()
            logger.debug(f"Cache MISS: {key}")

        return result

    def put_track_by_index(self, index: int, track: Any, ast_version: Optional[str] = None) -> None:
        """
        Cache track by index.

        Args:
            index: Track index
            track: TrackNode to cache
            ast_version: Optional AST version for automatic invalidation
        """
        if not self.enabled:
            return

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        key = f"track_{index}"
        self._track_by_index.put(key, track)
        logger.debug(f"Cached: {key}")

    # Scene lookups

    def get_scene_by_index(self, index: int, ast_version: Optional[str] = None) -> Optional[Any]:
        """
        Get cached scene by index.

        Args:
            index: Scene index
            ast_version: Optional AST version for automatic invalidation

        Returns:
            Cached SceneNode or None if not found
        """
        if not self.enabled:
            return None

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        key = f"scene_{index}"
        result = self._scene_by_index.get(key)

        if result is not None:
            self.stats.record_hit()
            logger.debug(f"Cache HIT: {key}")
        else:
            self.stats.record_miss()
            logger.debug(f"Cache MISS: {key}")

        return result

    def put_scene_by_index(self, index: int, scene: Any, ast_version: Optional[str] = None) -> None:
        """
        Cache scene by index.

        Args:
            index: Scene index
            scene: SceneNode to cache
            ast_version: Optional AST version for automatic invalidation
        """
        if not self.enabled:
            return

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        key = f"scene_{index}"
        self._scene_by_index.put(key, scene)
        logger.debug(f"Cached: {key}")

    # Bulk lookups (all tracks/scenes)

    def get_all_tracks(self, ast_version: Optional[str] = None) -> Optional[List]:
        """
        Get cached list of all tracks.

        Args:
            ast_version: Optional AST version for automatic invalidation

        Returns:
            Cached track list or None if not found
        """
        if not self.enabled:
            return None

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        if self._tracks_all is not None:
            self.stats.record_hit()
            logger.debug("Cache HIT: all_tracks")
        else:
            self.stats.record_miss()
            logger.debug("Cache MISS: all_tracks")

        return self._tracks_all

    def put_all_tracks(self, tracks: List, ast_version: Optional[str] = None) -> None:
        """
        Cache list of all tracks.

        Args:
            tracks: List of TrackNodes
            ast_version: Optional AST version for automatic invalidation
        """
        if not self.enabled:
            return

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        self._tracks_all = tracks
        logger.debug("Cached: all_tracks")

    def get_all_scenes(self, ast_version: Optional[str] = None) -> Optional[List]:
        """
        Get cached list of all scenes.

        Args:
            ast_version: Optional AST version for automatic invalidation

        Returns:
            Cached scene list or None if not found
        """
        if not self.enabled:
            return None

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        if self._scenes_all is not None:
            self.stats.record_hit()
            logger.debug("Cache HIT: all_scenes")
        else:
            self.stats.record_miss()
            logger.debug("Cache MISS: all_scenes")

        return self._scenes_all

    def put_all_scenes(self, scenes: List, ast_version: Optional[str] = None) -> None:
        """
        Cache list of all scenes.

        Args:
            scenes: List of SceneNodes
            ast_version: Optional AST version for automatic invalidation
        """
        if not self.enabled:
            return

        # Auto-invalidate if version changed
        if ast_version is not None:
            self.set_version(ast_version)

        self._scenes_all = scenes
        logger.debug("Cached: all_scenes")

    # Statistics

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'enabled': self.enabled,
            'capacity': self.capacity,
            'current_version': self._current_version,
            'cache_sizes': {
                'track_by_index': self._track_by_index.size(),
                'scene_by_index': self._scene_by_index.size(),
                'all_tracks_cached': self._tracks_all is not None,
                'all_scenes_cached': self._scenes_all is not None,
            },
            'statistics': self.stats.to_dict(),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.stats.reset()
