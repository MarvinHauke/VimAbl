"""
Parser module for Ableton Live project files.

This module handles:
- Loading and decompressing .als files
- Extracting file references and hashes
- Extracting track and device information
- Building the initial AST structure from XML
"""

from .xml_loader import load_ableton_xml
from .file_refs import extract_file_refs
from .tracks import extract_tracks
from .ast_builder import build_ast

__all__ = [
    "load_ableton_xml",
    "extract_file_refs",
    "extract_tracks",
    "build_ast",
]
