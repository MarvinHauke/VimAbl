"""
Server module for LSP-like interface to Ableton Live projects.

This module provides:
- API server for querying and manipulating AST
- File watcher for detecting changes to .als files
- Future: LSP protocol implementation
"""

from .api import ASTServer

# Make FileWatcher optional (requires watchdog)
try:
    from .watcher import FileWatcher
    __all__ = ["ASTServer", "FileWatcher"]
except ImportError:
    __all__ = ["ASTServer"]
