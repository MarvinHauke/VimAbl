"""
Centralized logging configuration for VimAbl Remote Script.

PERFORMANCE IMPACT:
- Logging has ~10-20% CPU overhead in Python Remote Scripts
- Disable logging in production for better performance
- Critical errors always logged regardless of setting

USAGE:
    from .logging_config import log, ENABLE_LOGGING

    # In your module
    log("INFO", "Something happened")
    log("ERROR", "Critical error", force=True)  # Always logged

    # Toggle logging globally
    ENABLE_LOGGING = False  # Set to False for production
"""

# ============================================================================
# GLOBAL LOGGING CONFIGURATION
# ============================================================================

# Set to False to disable all logging for better performance (~10-20% CPU reduction)
# Critical errors (force=True) will still be logged
ENABLE_LOGGING = True


def log(prefix: str, message: str, force: bool = False):
    """
    Log a message to Ableton's log file.

    Args:
        prefix: Log prefix (e.g., "UDPSender", "TrackObserver")
        message: Message to log
        force: If True, log even if ENABLE_LOGGING is False (for critical errors)

    Examples:
        log("UDPSender", "Started on port 9002")
        log("TrackObserver", "ERROR: Failed to observe track", force=True)
    """
    if ENABLE_LOGGING or force:
        print(f"[{prefix}] {message}")


def log_simple(message: str, force: bool = False):
    """
    Log a simple message without prefix.

    Args:
        message: Message to log
        force: If True, log even if ENABLE_LOGGING is False

    Examples:
        log_simple("Live State Remote Script initialized")
        log_simple("CRITICAL ERROR: System failure", force=True)
    """
    if ENABLE_LOGGING or force:
        print(message)
