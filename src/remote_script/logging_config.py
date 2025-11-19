"""
Optimized centralized logging for VimAbl Remote Script.

GOALS:
- Zero Live API calls outside main thread
- Ultra-low overhead (optimized string ops + reduced globals)
- Adaptive draining (no dropped logs under heavy load)
- Supports severity levels
- Performance metrics tracking
- Safe on Live reloads

USAGE:
    # In LiveState.__init__()
    from .logging_config import init_logging
    init_logging(self.log_message)

    # Inside update_display()
    from .logging_config import drain_log_queue
    drain_log_queue()

    # From any thread / module:
    from .logging_config import log
    log("OSC", "Started server", level="INFO")
    log("UDP", "Packet dropped", level="WARN")
    log("ERROR", "Critical failure", level="ERROR")

    # Get performance metrics:
    from .logging_config import get_log_stats
    stats = get_log_stats()
    # Returns: {
    #   "queue_size": 0,              # Current messages in queue
    #   "queue_max": 2000,            # Max queue capacity
    #   "queue_utilization": 0.0,     # Percentage used (0-100)
    #   "messages_enqueued": 1234,    # Total messages sent
    #   "messages_dropped": 0,        # Messages lost (queue full)
    #   "messages_drained": 1234,     # Messages written to log
    #   "peak_queue_size": 45,        # Highest queue size reached
    #   "drop_rate": 0.0              # Drop percentage (0-100)
    # }
"""

import queue
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Main setting to reduce CPU usage.
ENABLE_LOGGING = True

# Filtering by severity (fast set lookup)
ENABLED_LEVELS = {"INFO", "WARN", "ERROR", "CRITICAL"}

# Thread-safe queue with a cap to avoid runaway memory
_log_queue = queue.Queue(maxsize=2000)

# Main-thread log callback (ControlSurface.log_message)
_log_callback = None

# Cached references for speed (micro-optimizations)
_q_put = _log_queue.put_nowait
_q_get = _log_queue.get_nowait
_empty = queue.Empty

# Performance metrics
_messages_enqueued = 0
_messages_dropped = 0
_messages_drained = 0
_peak_queue_size = 0


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_logging(log_callback):
    """
    Must be called once from the main ControlSurface.

    Args:
        log_callback: reference to ControlSurface.log_message
    """
    global _log_callback, _messages_enqueued, _messages_dropped, _messages_drained, _peak_queue_size
    _log_callback = log_callback
    # Reset metrics on init
    _messages_enqueued = 0
    _messages_dropped = 0
    _messages_drained = 0
    _peak_queue_size = 0


# ============================================================================
# PRODUCER SIDE — THREAD SAFE
# ============================================================================

def log(component: str, message: str, level: str = "INFO", force: bool = False):
    """
    Public logging function — usable from any thread.

    Args:
        component: e.g. "OSC", "TrackObserver"
        message: log text
        level: "DEBUG" / "INFO" / "WARN" / "ERROR" / "CRITICAL"
        force: log even when logging is disabled

    Examples:
        log("UDPSender", "Started on port 9002", level="INFO")
        log("TrackObserver", "Failed to observe track", level="ERROR", force=True)
    """
    if not force:
        if not ENABLE_LOGGING:
            return
        if level not in ENABLED_LEVELS:
            return

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Put a tuple instead of formatting a string here (faster)
    try:
        _q_put((timestamp, level, component, message))

        # Track metrics
        global _messages_enqueued, _peak_queue_size
        _messages_enqueued += 1

        # Update peak queue size
        try:
            current_size = _log_queue.qsize()
            if current_size > _peak_queue_size:
                _peak_queue_size = current_size
        except Exception:
            pass

    except queue.Full:
        # Track dropped messages
        global _messages_dropped
        _messages_dropped += 1
    except Exception:
        # Drop silently — logger should never block or crash
        pass


# ============================================================================
# MAIN THREAD — FORMAT & WRITE TO ABLETON LOG
# ============================================================================

def drain_log_queue(max_messages=200):
    """
    Called from update_display() (~60Hz) on the main Ableton thread.

    Adaptive draining:
    - If backlog is small → drain up to max_messages
    - If backlog is large → drain more to catch up

    Args:
        max_messages: Base limit for messages to drain per call
    """
    if _log_callback is None:
        return

    try:
        qsize = _log_queue.qsize()
    except Exception:
        qsize = 0

    # Adaptive limit: if queue is too big, drain more aggressively
    limit = max(max_messages, qsize // 2)

    count = 0

    while count < limit:
        try:
            timestamp, level, component, message = _q_get()
        except _empty:
            break

        # Final formatting happens HERE — on the main thread
        formatted = f"[{timestamp}] [{level}] [{component}] {message}"

        try:
            _log_callback(formatted)
        except Exception:
            pass

        count += 1

    # Track drained messages
    if count > 0:
        global _messages_drained
        _messages_drained += count


def clear_log_queue():
    """Clear queue on shutdown (optional)."""
    try:
        while True:
            _q_get()
    except _empty:
        pass


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

def get_log_stats():
    """
    Get logging performance metrics.

    Returns:
        dict: Performance metrics including:
            - queue_size: Current number of messages in queue
            - queue_max: Maximum queue capacity
            - queue_utilization: Percentage of queue capacity used (0-100)
            - messages_enqueued: Total messages sent to queue
            - messages_dropped: Messages lost due to full queue
            - messages_drained: Messages successfully written to log
            - peak_queue_size: Highest queue size reached
            - drop_rate: Percentage of messages dropped (0-100)
    """
    try:
        current_size = _log_queue.qsize()
    except Exception:
        current_size = 0

    max_size = _log_queue.maxsize
    utilization = (current_size / max_size * 100) if max_size > 0 else 0
    drop_rate = (_messages_dropped / _messages_enqueued * 100) if _messages_enqueued > 0 else 0

    return {
        "queue_size": current_size,
        "queue_max": max_size,
        "queue_utilization": round(utilization, 1),
        "messages_enqueued": _messages_enqueued,
        "messages_dropped": _messages_dropped,
        "messages_drained": _messages_drained,
        "peak_queue_size": _peak_queue_size,
        "drop_rate": round(drop_rate, 2)
    }


def reset_log_stats():
    """Reset performance metrics counters."""
    global _messages_enqueued, _messages_dropped, _messages_drained, _peak_queue_size
    _messages_enqueued = 0
    _messages_dropped = 0
    _messages_drained = 0
    _peak_queue_size = 0
