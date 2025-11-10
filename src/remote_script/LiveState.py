"""
Main Remote Script controller that observes Live's state
"""

import Live
import socket
import threading
import json
from _Framework.ControlSurface import ControlSurface


class LiveState(ControlSurface):
    """Observes Live state and exposes it via a local socket server"""

    def __init__(self, c_instance):
        super().__init__(c_instance)

        self.application = Live.Application.get_application()

        self.current_view = "session"  # Default to session view
        self.browser_visible = False
        self.device_visible = False
        self.clip_view_visible = False
        self.detail_view = "device"  # "device" or "clip"
        self.groove_pool_visible = False
        self.info_view_visible = False

        # Thread-safe command execution
        self._pending_command = None
        self._command_result = None
        self._command_lock = threading.Lock()
        self._result_ready = threading.Event()

        # Setup view observer
        self._setup_observers()

        # Register command handlers
        self._command_handlers = self._register_commands()

        # Start server in background thread
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        self.log_message("Live State Remote Script initialized")

    def _setup_observers(self):
        """Setup observers for view changes"""
        view = self.application.view

        # Add observers for view changes (with error handling for duplicates)
        try:
            view.add_is_view_visible_listener("Session", self._on_view_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Arranger", self._on_view_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Browser", self._on_browser_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Detail", self._on_device_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Detail/DeviceChain", self._on_device_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Detail/Clip", self._on_clip_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("GroovePool", self._on_groove_pool_changed)
        except RuntimeError:
            pass  # Observer already connected

        try:
            view.add_is_view_visible_listener("Help", self._on_info_view_changed)
        except RuntimeError:
            pass  # Observer already connected

    def _on_view_changed(self):
        """Called when view visibility changes"""
        view = self.application.view

        if view.is_view_visible("Arranger"):
            self.current_view = "arrangement"
            self.log_message("Switched to Arrangement view")
        elif view.is_view_visible("Session"):
            self.current_view = "session"
            self.log_message("Switched to Session view")

    def _on_browser_changed(self):
        """Called when browser visibility changes"""
        view = self.application.view
        self.browser_visible = view.is_view_visible("Browser")
        self.log_message(f"Browser visible: {self.browser_visible}")

    def _on_device_changed(self):
        """Called when device view visibility changes"""
        view = self.application.view
        self.device_visible = view.is_view_visible("Detail") or view.is_view_visible("Detail/DeviceChain")

        # Update which detail view is active
        if view.is_view_visible("Detail/DeviceChain"):
            self.detail_view = "device"

        self.log_message(f"Device view visible: {self.device_visible}, detail_view: {self.detail_view}")

    def _on_clip_changed(self):
        """Called when clip view visibility changes"""
        view = self.application.view
        self.clip_view_visible = view.is_view_visible("Detail/Clip")

        # Update which detail view is active
        if self.clip_view_visible:
            self.detail_view = "clip"

        self.log_message(f"Clip view visible: {self.clip_view_visible}, detail_view: {self.detail_view}")

    def _on_groove_pool_changed(self):
        """Called when groove pool visibility changes"""
        view = self.application.view
        self.groove_pool_visible = view.is_view_visible("GroovePool")
        self.log_message(f"Groove Pool visible: {self.groove_pool_visible}")

    def _on_info_view_changed(self):
        """Called when info view visibility changes"""
        view = self.application.view
        self.info_view_visible = view.is_view_visible("Help")
        self.log_message(f"Info View visible: {self.info_view_visible}")

    def _execute_in_main_thread(self, handler, params=None):
        """Execute handler in main thread using schedule_message"""
        with self._command_lock:
            self._pending_command = (handler, params)
            self._command_result = None
            self._result_ready.clear()

        # Schedule execution in main thread (0 = ASAP, not next tick)
        self.schedule_message(0, self._execute_pending_command)

        # Wait for result (with timeout)
        if self._result_ready.wait(timeout=1.0):
            return self._command_result
        else:
            return {"success": False, "error": "Command timeout"}

    def _execute_pending_command(self):
        """Called in main thread to execute pending command"""
        with self._command_lock:
            if self._pending_command:
                handler, params = self._pending_command
                try:
                    self._command_result = handler(params)
                except Exception as e:
                    self._command_result = {"success": False, "error": str(e)}
                finally:
                    self._pending_command = None
                    self._result_ready.set()

    def _register_commands(self):
        """Register all command handlers

        Commands are categorized:
        - Direct: Can execute immediately without thread switching (read-only, no self.song())
        - Threaded: Must execute in main thread (accesses self.song())
        """
        return {
            "GET_VIEW": self._handle_get_view,           # Direct - no self.song() access
            "GET_STATE": self._handle_get_state,         # Threaded - needs self.song().is_playing
            "SELECT_FIRST_SCENE": self._handle_select_first_scene,
            "SELECT_LAST_SCENE": self._handle_select_last_scene,
            "SELECT_FIRST_TRACK": self._handle_select_first_track,
            "SELECT_LAST_TRACK": self._handle_select_last_track,
            "SCROLL_TO_TOP": self._handle_scroll_to_top,
            "SCROLL_TO_BOTTOM": self._handle_scroll_to_bottom,
        }

    def _get_direct_commands(self):
        """Commands that can execute immediately without thread switching"""
        return {"GET_VIEW"}

    def _handle_get_view(self, params=None):
        """Handle GET_VIEW command (fast path - no thread switching)"""
        # Always check current state instead of relying on cached value
        view = self.application.view
        if view.is_view_visible("Arranger"):
            current = "arrangement"
        elif view.is_view_visible("Session"):
            current = "session"
        else:
            current = self.current_view  # Fallback to cached value

        return {
            "view": current
        }

    def _handle_get_state(self, params=None):
        """Handle GET_STATE command"""
        return {
            "view": self.current_view,
            "transport_playing": self.song().is_playing,
            "browser_visible": self.browser_visible,
            "device_visible": self.device_visible,
            "clip_view_visible": self.clip_view_visible,
            "detail_view": self.detail_view,
            "groove_pool_visible": self.groove_pool_visible,
            "info_view_visible": self.info_view_visible
        }

    def _handle_select_first_scene(self, params=None):
        """Handle SELECT_FIRST_SCENE command"""
        try:
            scenes = self.song().scenes
            if len(scenes) > 0:
                self.song().view.selected_scene = scenes[0]
                return {"success": True}
            else:
                return {"success": False, "error": "No scenes"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_select_last_scene(self, params=None):
        """Handle SELECT_LAST_SCENE command"""
        try:
            scenes = self.song().scenes
            if len(scenes) > 0:
                self.song().view.selected_scene = scenes[-1]
                return {"success": True}
            else:
                return {"success": False, "error": "No scenes"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_select_first_track(self, params=None):
        """Handle SELECT_FIRST_TRACK command"""
        try:
            tracks = self.song().tracks
            if len(tracks) > 0:
                self.song().view.selected_track = tracks[0]
                # Force view to scroll to the selected track
                self.application.view.show_view("Arranger")
                self.log_message("Selected first track and scrolled view")
                return {"success": True}
            else:
                return {"success": False, "error": "No tracks"}
        except Exception as e:
            self.log_message(f"Select first track failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_select_last_track(self, params=None):
        """Handle SELECT_LAST_TRACK command"""
        try:
            tracks = self.song().tracks
            if len(tracks) > 0:
                self.song().view.selected_track = tracks[-1]
                # Force view to scroll to the selected track
                self.application.view.show_view("Arranger")
                self.log_message("Selected last track and scrolled view")
                return {"success": True}
            else:
                return {"success": False, "error": "No tracks"}
        except Exception as e:
            self.log_message(f"Select last track failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_scroll_to_top(self, params=None):
        """Handle SCROLL_TO_TOP command"""
        try:
            # Jump to beginning of arrangement
            self.song().current_song_time = 0.0
            self.log_message("Scrolled to top (time = 0)")
            return {"success": True}
        except Exception as e:
            self.log_message(f"Scroll to top failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_scroll_to_bottom(self, params=None):
        """Handle SCROLL_TO_BOTTOM command"""
        try:
            # Jump to end of arrangement (last cue point or song length)
            song_length = self.song().last_event_time
            self.song().current_song_time = song_length
            self.log_message(f"Scrolled to bottom (time = {song_length})")
            return {"success": True}
        except Exception as e:
            self.log_message(f"Scroll to bottom failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _run_server(self):
        """Run a simple socket server to expose state to Hammerspoon"""
        HOST = '127.0.0.1'
        PORT = 9001

        # Outer try-catch for server setup only
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((HOST, PORT))
                s.listen(1)
                self.log_message(f"Server listening on {HOST}:{PORT}")

                while True:
                    try:
                        # Handle each connection in its own try-catch
                        conn, addr = s.accept()
                        with conn:
                            data = conn.recv(1024)
                            if data:
                                request = data.decode('utf-8').strip()

                                # Parse command and optional parameters (format: COMMAND:param1:param2)
                                parts = request.split(':')
                                command = parts[0]
                                params = parts[1:] if len(parts) > 1 else None

                                # Dispatch to handler
                                handler = self._command_handlers.get(command)
                                if handler:
                                    try:
                                        # Check if command can execute directly (no thread switching)
                                        if command in self._get_direct_commands():
                                            # Fast path: execute immediately (no logging for speed)
                                            result = handler(params)
                                        else:
                                            # Slow path: execute in main thread for thread safety
                                            self.log_message(f"Executing command: {command}")
                                            result = self._execute_in_main_thread(handler, params)

                                        response = json.dumps(result)
                                    except Exception as e:
                                        error_msg = f"Handler error for {command}: {str(e)}"
                                        self.log_message(error_msg)
                                        response = json.dumps({"success": False, "error": str(e)})
                                else:
                                    error_msg = f"Unknown command: {command}"
                                    self.log_message(error_msg)
                                    response = json.dumps({
                                        "success": False,
                                        "error": error_msg
                                    })

                                conn.sendall(response.encode('utf-8'))
                    except Exception as e:
                        # Log connection errors but keep server running
                        self.log_message(f"Connection error: {str(e)}")
                        continue
        except Exception as e:
            self.log_message(f"Fatal server error: {str(e)}")

    def disconnect(self):
        """Called when script is disconnected"""
        self.log_message("Live State Remote Script disconnecting")

        # Remove observers
        view = self.application.view
        try:
            view.remove_is_view_visible_listener("Session", self._on_view_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Arranger", self._on_view_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Browser", self._on_browser_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Detail", self._on_device_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Detail/DeviceChain", self._on_device_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Detail/Clip", self._on_clip_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("GroovePool", self._on_groove_pool_changed)
        except RuntimeError:
            pass

        try:
            view.remove_is_view_visible_listener("Help", self._on_info_view_changed)
        except RuntimeError:
            pass

        super().disconnect()
