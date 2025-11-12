"""
Command handlers for Live API operations
"""


class CommandHandlers:
    """Handles all commands from Hammerspoon"""

    def __init__(self, song_accessor, application, observers, log_callback, udp_observer_manager=None):
        """Initialize command handlers

        Args:
            song_accessor: Function that returns Live.Song instance (e.g., self.song)
            application: Live.Application instance
            observers: ViewObservers instance for state access
            log_callback: Function to call for logging (e.g., self.log_message)
            udp_observer_manager: ObserverManager instance for UDP observers (optional)
        """
        self.song = song_accessor
        self.application = application
        self.observers = observers
        self.log_message = log_callback
        self.udp_observer_manager = udp_observer_manager

    def register_commands(self):
        """Register all command handlers

        Commands are categorized:
        - Direct: Can execute immediately without thread switching (read-only, no self.song())
        - Threaded: Must execute in main thread (accesses self.song())
        """
        commands = {
            "GET_VIEW": self._handle_get_view,           # Direct - no self.song() access
            "GET_STATE": self._handle_get_state,         # Threaded - needs self.song().is_playing
            "EXPORT_XML": self._handle_export_xml,       # Threaded - saves the project as XML (requires project_path param)
            "SCROLL_TO_TOP": self._handle_scroll_to_top,
            "SCROLL_TO_BOTTOM": self._handle_scroll_to_bottom,
            "JUMP_TO_FIRST": self._handle_jump_to_first,  # Smart command - auto-detects view
            "JUMP_TO_LAST": self._handle_jump_to_last,    # Smart command - auto-detects view
        }

        # Add UDP observer commands if available
        if self.udp_observer_manager:
            commands.update({
                "START_OBSERVERS": self._handle_start_observers,     # Start UDP observers
                "STOP_OBSERVERS": self._handle_stop_observers,       # Stop UDP observers
                "REFRESH_OBSERVERS": self._handle_refresh_observers, # Refresh UDP observers
                "GET_OBSERVER_STATUS": self._handle_get_observer_status, # Get observer statistics
            })

        return commands

    def get_direct_commands(self):
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
            current = self.observers.current_view  # Fallback to cached value

        return {
            "view": current
        }

    def _handle_export_xml(self, params=None):
        """Handle EXPORT_XML command - exports project as XML to .vimabl directory

        Args:
            params: list with project path as first element (colon-delimited format: EXPORT_XML:path).
                    Project path is always provided by hs.pathwatcher from Hammerspoon.
        """
        try:
            import os
            import gzip

            # Project path must be provided by Hammerspoon
            if not params or not isinstance(params, list) or len(params) == 0:
                self.log_message("Export: ERROR - No project path provided")
                return {
                    "success": False,
                    "error": "Project path is required (provided by Hammerspoon)"
                }

            project_path = params[0]
            self.log_message(f"Export: Using project path from Hammerspoon: {project_path}")

            # Extract project directory and name
            project_dir = os.path.dirname(project_path)
            project_name = os.path.splitext(os.path.basename(project_path))[0]

            # Create .vimabl directory
            vimabl_dir = os.path.join(project_dir, ".vimabl")
            if not os.path.exists(vimabl_dir):
                os.makedirs(vimabl_dir)
                self.log_message(f"Created .vimabl directory: {vimabl_dir}")

            # Extract XML from .als file (which is gzipped XML)
            xml_path = os.path.join(vimabl_dir, f"{project_name}.xml")

            with gzip.open(project_path, 'rb') as f_in:
                with open(xml_path, 'wb') as f_out:
                    f_out.write(f_in.read())

            self.log_message(f"Extracted XML from .als file: {xml_path}")
            return {
                "success": True,
                "xml_path": xml_path,
                "project_path": project_path
            }
        except Exception as e:
            self.log_message(f"Failed to export XML: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _handle_get_state(self, params=None):
        """Handle GET_STATE command"""
        state = self.observers.get_state()
        state["transport_playing"] = self.song().is_playing
        return state

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

    def _handle_jump_to_first(self, params=None):
        """Handle JUMP_TO_FIRST command - auto-detects view and jumps to first track/scene"""
        try:
            view = self.application.view

            if view.is_view_visible("Arranger"):
                # Arrangement view: Select first track
                tracks = self.song().tracks
                if len(tracks) > 0:
                    self.song().view.selected_track = tracks[0]
                    self.application.view.show_view("Arranger")
                    self.log_message("Jumped to first track (arrangement)")
                    return {"success": True}
                else:
                    return {"success": False, "error": "No tracks"}
            else:
                # Session view: Select first scene
                scenes = self.song().scenes
                if len(scenes) > 0:
                    self.song().view.selected_scene = scenes[0]
                    self.log_message("Jumped to first scene (session)")
                    return {"success": True}
                else:
                    return {"success": False, "error": "No scenes"}
        except Exception as e:
            self.log_message(f"Jump to first failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_jump_to_last(self, params=None):
        """Handle JUMP_TO_LAST command - auto-detects view and jumps to last track/scene"""
        try:
            view = self.application.view

            if view.is_view_visible("Arranger"):
                # Arrangement view: Select last track
                tracks = self.song().tracks
                if len(tracks) > 0:
                    self.song().view.selected_track = tracks[-1]
                    self.application.view.show_view("Arranger")
                    self.log_message("Jumped to last track (arrangement)")
                    return {"success": True}
                else:
                    return {"success": False, "error": "No tracks"}
            else:
                # Session view: Select last scene
                scenes = self.song().scenes
                if len(scenes) > 0:
                    self.song().view.selected_scene = scenes[-1]
                    self.log_message("Jumped to last scene (session)")
                    return {"success": True}
                else:
                    return {"success": False, "error": "No scenes"}
        except Exception as e:
            self.log_message(f"Jump to last failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_start_observers(self, params=None):
        """Handle START_OBSERVERS command - start UDP observers"""
        try:
            if not self.udp_observer_manager:
                return {"success": False, "error": "UDP observer manager not initialized"}

            self.udp_observer_manager.start()
            self.log_message("UDP observers started")
            return {
                "success": True,
                "message": "UDP observers started",
                "stats": self.udp_observer_manager.get_stats()
            }
        except Exception as e:
            self.log_message(f"Failed to start observers: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_stop_observers(self, params=None):
        """Handle STOP_OBSERVERS command - stop UDP observers"""
        try:
            if not self.udp_observer_manager:
                return {"success": False, "error": "UDP observer manager not initialized"}

            self.udp_observer_manager.stop()
            self.log_message("UDP observers stopped")
            return {
                "success": True,
                "message": "UDP observers stopped"
            }
        except Exception as e:
            self.log_message(f"Failed to stop observers: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_refresh_observers(self, params=None):
        """Handle REFRESH_OBSERVERS command - refresh UDP observers"""
        try:
            if not self.udp_observer_manager:
                return {"success": False, "error": "UDP observer manager not initialized"}

            self.udp_observer_manager.refresh()
            self.log_message("UDP observers refreshed")
            return {
                "success": True,
                "message": "UDP observers refreshed",
                "stats": self.udp_observer_manager.get_stats()
            }
        except Exception as e:
            self.log_message(f"Failed to refresh observers: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_get_observer_status(self, params=None):
        """Handle GET_OBSERVER_STATUS command - get observer statistics"""
        try:
            if not self.udp_observer_manager:
                return {"success": False, "error": "UDP observer manager not initialized"}

            stats = self.udp_observer_manager.get_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            self.log_message(f"Failed to get observer status: {str(e)}")
            return {"success": False, "error": str(e)}
