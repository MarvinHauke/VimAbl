"""
Main Remote Script controller that observes Live's state

PERFORMANCE TUNING:
-------------------
Logging is controlled centrally in logging_config.py
Set ENABLE_LOGGING = False for better performance
"""

import Live
from _Framework.ControlSurface import ControlSurface
from _Framework import Task

from .observers import ViewObservers, ObserverManager
from .commands import CommandHandlers
from .server import CommandServer
from .udp_sender import UDPSender
from .cursor_observer import SessionCursorObserver
from .logging_config import init_logging, drain_log_queue, clear_log_queue, log, get_log_stats

# Task constants
RUNNING = 1
KILLED = 0


class LiveState(ControlSurface):
    """Observes Live state and exposes it via a local socket server"""

    def __init__(self, c_instance):
        super().__init__(c_instance)

        # Initialize thread-safe logging FIRST
        init_logging(self.log_message)

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

        # Schedule recurring tasks via _Framework.Task (runs in update_display loop)
        # This keeps update_display() minimal and delegates polling to Task scheduler
        self._setup_tasks()

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

    def _setup_tasks(self):
        """
        Set up recurring tasks using _Framework.Task scheduler.

        This delegates polling logic to the Task system, keeping update_display()
        minimal and performant. Tasks run every frame (~60Hz) via the parent
        ControlSurface._task_group which is updated in update_display().
        """
        try:
            # Initialize stats counter
            self._stats_tick_counter = 0

            # Task 1: Poll observer manager for debounce/batching (every frame)
            observer_task = Task.FuncTask(func=self._poll_observer_manager)
            self._task_group.add(observer_task)

            # Task 2: Poll cursor observer for highlighted_clip_slot (every frame)
            cursor_task = Task.FuncTask(func=self._poll_cursor_observer)
            self._task_group.add(cursor_task)

            # Task 3: Log performance stats (every 5 minutes at 60Hz = 18000 ticks)
            stats_task = Task.FuncTask(func=self._log_stats_periodically)
            self._task_group.add(stats_task)

            log("LiveState", "✓ Scheduled 3 recurring tasks via _Framework.Task", level="INFO")
        except Exception as e:
            log("LiveState", f"ERROR setting up tasks: {e}", level="ERROR", force=True)
            # Fall back to old behavior if task setup fails
            self._task_setup_failed = True

    def _poll_observer_manager(self, delta):
        """
        Task callback: Check for trailing edge debounce events.
        Called every frame by Task scheduler.
        """
        try:
            if hasattr(self, 'udp_observer_manager'):
                self.udp_observer_manager.update()
        except Exception as e:
            log("LiveState", f"Error in observer manager task: {e}", level="ERROR", force=True)
        return RUNNING  # Keep task alive

    def _poll_cursor_observer(self, delta):
        """
        Task callback: Update cursor observer (polls highlighted_clip_slot).
        Called every frame by Task scheduler.
        """
        try:
            if hasattr(self, 'cursor_observer'):
                self.cursor_observer.update()
        except Exception as e:
            log("LiveState", f"Error in cursor observer task: {e}", level="ERROR", force=True)
        return RUNNING  # Keep task alive

    def _log_stats_periodically(self, delta):
        """
        Task callback: Log performance stats every 5 minutes.
        Called every frame by Task scheduler.
        """
        try:
            self._stats_tick_counter += 1
            if self._stats_tick_counter >= 18000:  # 60Hz * 60s * 5min
                stats = get_log_stats()
                log("LiveState",
                    f"Logging stats: {stats['messages_drained']} drained, "
                    f"{stats['messages_dropped']} dropped ({stats['drop_rate']}%), "
                    f"peak queue: {stats['peak_queue_size']}/{stats['queue_max']}",
                    level="INFO")
                self._stats_tick_counter = 0
        except Exception as e:
            log("LiveState", f"Error in stats logging task: {e}", level="ERROR", force=True)
        return RUNNING  # Keep task alive

    def update_display(self):
        """
        The fastest possible update loop for a heavy Ableton Remote Script.

        Responsibilities (only):
        - Drain logger queue (cheap, micro-optimized)
        - Let _Framework.Task run its scheduled tasks
        - DO NOT do any logic, debounce, polling, or model building here

        Performance: This is called at ~60Hz by Ableton Live's main thread.
        Any code here must be extremely lightweight to avoid audio dropouts.
        """
        # 1. Drain any queued log entries (micro-optimized queue)
        try:
            drain_log_queue()
        except Exception:
            pass  # Logging must never break the display loop

        # 2. Run Ableton's task system (executes our scheduled tasks above)
        super(LiveState, self).update_display()

        # 3. Fallback: If task setup failed, use old polling method
        if hasattr(self, '_task_setup_failed') and self._task_setup_failed:
            try:
                if hasattr(self, 'udp_observer_manager'):
                    self.udp_observer_manager.update()
                if hasattr(self, 'cursor_observer'):
                    self.cursor_observer.update()
            except Exception:
                pass

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
