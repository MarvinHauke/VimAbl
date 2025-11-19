"""
Main Remote Script controller that observes Live's state

PERFORMANCE TUNING:
-------------------
Logging is controlled centrally in logging_config.py
Set ENABLE_LOGGING = False for better performance
"""

import Live
from _Framework.ControlSurface import ControlSurface

from .observers import ViewObservers, ObserverManager
from .commands import CommandHandlers
from .server import CommandServer
from .udp_sender import UDPSender
from .cursor_observer import SessionCursorObserver
from .logging_config import init_logging, drain_log_queue, clear_log_queue, log, get_log_stats


class LiveState(ControlSurface):
    """Observes Live state and exposes it via a local socket server"""

    def __init__(self, c_instance):
        super().__init__(c_instance)

        # Initialize thread-safe logging FIRST
        init_logging(self.log_message)

        # Stats logging counter (log every 5 minutes at 60Hz = 18000 updates)
        self._stats_counter = 0

        self.application = Live.Application.get_application()

        # Initialize view observers
        self.observers = ViewObservers(self.application, self.log_message)
        self.observers.setup()

        # Initialize UDP sender for real-time events
        self.udp_sender = UDPSender(host="127.0.0.1", port=9002)
        self.udp_sender.start()
        log("LiveState", "UDP sender initialized on 127.0.0.1:9002", level="INFO")

        # Initialize Live API observers (tracks, devices, transport)
        self.udp_observer_manager = ObserverManager(
            song=self.song(),
            udp_sender=self.udp_sender
        )
        self.udp_observer_manager.start()
        log("LiveState", "UDP observer manager started", level="INFO")

        # Initialize Session View cursor observer
        self.cursor_observer = SessionCursorObserver(
            song=self.song(),
            sender=self.udp_sender,
            log_func=self.log_message
        )
        log("LiveState", "Session cursor observer initialized", level="INFO")

        # Initialize command handlers
        self.command_handlers = CommandHandlers(
            song_accessor=self.song,
            application=self.application,
            observers=self.observers,
            log_callback=self.log_message,
            udp_observer_manager=self.udp_observer_manager
        )

        # Initialize and start server
        self.server = CommandServer(
            command_handlers=self.command_handlers,
            schedule_callback=self.schedule_message,
            log_callback=self.log_message
        )
        self.server.start()

        # Listen for document path changes (e.g., Save As, first save)
        self._setup_document_listener()

        log("LiveState", "Live State Remote Script initialized", level="INFO")

    def _setup_document_listener(self):
        """Set up listener for document path changes"""
        try:
            document = self.application.get_document()
            if document and hasattr(document, 'add_path_listener'):
                document.add_path_listener(self._on_document_path_changed)
                log("LiveState", "Document path listener added", level="INFO")
        except Exception as e:
            log("LiveState", f"Failed to add document listener: {str(e)}", level="ERROR")

    def _on_document_path_changed(self):
        """Called when the document path changes (e.g., after Save As or first save)"""
        try:
            document = self.application.get_document()
            if document and document.path:
                path = str(document.path)
                log("LiveState", f"Document path changed to: {path}", level="INFO")
                # Broadcast the path change via the server
                # This allows Hammerspoon/WebSocket to react to the save
                self.server.broadcast_event("PROJECT_PATH_CHANGED", {"project_path": path})
        except Exception as e:
            log("LiveState", f"Error in document path listener: {str(e)}", level="ERROR")

    def update_display(self):
        """
        Called periodically by Ableton Live's main loop (~60Hz).
        
        - Drains log queue (thread-safe logging)
        - Checks for trailing edge debounce events
        - Polls cursor observer state
        """
        super(LiveState, self).update_display()

        # Drain log queue on main thread (MUST be first for thread safety)
        drain_log_queue()

        # Periodically log performance stats (every 5 minutes)
        self._stats_counter += 1
        if self._stats_counter >= 18000:  # 60Hz * 60s * 5min
            stats = get_log_stats()
            log("LiveState",
                f"Logging stats: {stats['messages_drained']} drained, "
                f"{stats['messages_dropped']} dropped ({stats['drop_rate']}%), "
                f"peak queue: {stats['peak_queue_size']}/{stats['queue_max']}",
                level="INFO")
            self._stats_counter = 0

        # Check for trailing edge debounce events
        if hasattr(self, 'udp_observer_manager'):
            self.udp_observer_manager.update()

        # Update cursor observer (polls highlighted_clip_slot)
        if hasattr(self, 'cursor_observer'):
            self.cursor_observer.update()

    def disconnect(self):
        """Called when script is disconnected"""
        log("LiveState", "Live State Remote Script disconnecting", level="INFO")

        # Disconnect cursor observer
        if hasattr(self, 'cursor_observer'):
            self.cursor_observer.disconnect()
            log("LiveState", "Cursor observer disconnected", level="INFO")

        # Stop UDP observer manager
        if hasattr(self, 'udp_observer_manager'):
            self.udp_observer_manager.stop()
            log("LiveState", "UDP observer manager stopped", level="INFO")

        # Stop UDP sender
        if hasattr(self, 'udp_sender'):
            self.udp_sender.stop()
            log("LiveState", "UDP sender stopped", level="INFO")

        # Remove view observers
        self.observers.teardown()

        # Log final stats before shutdown
        stats = get_log_stats()
        log("LiveState",
            f"Final logging stats: {stats['messages_enqueued']} total messages, "
            f"{stats['messages_drained']} drained, {stats['messages_dropped']} dropped "
            f"({stats['drop_rate']}% drop rate), peak queue: {stats['peak_queue_size']}/{stats['queue_max']}",
            level="INFO")

        # Clear and drain remaining log messages
        drain_log_queue(max_messages=1000)  # Drain all remaining
        clear_log_queue()

        super().disconnect()
