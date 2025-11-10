"""
Ableton Live Remote Script for LSP-like functionality
Observes application state and exposes it via a local server
"""

from .LiveState import LiveState

def create_instance(c_instance):
    """Required entry point for Ableton Live Remote Scripts"""
    return LiveState(c_instance)
