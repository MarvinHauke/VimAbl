"""
Command handlers for Live API operations
"""


class CommandHandlers:
    """Handles all commands from Hammerspoon"""

    def __init__(self, song_accessor, application, observers, log_callback):
        """Initialize command handlers

        Args:
            song_accessor: Function that returns Live.Song instance (e.g., self.song)
            application: Live.Application instance
            observers: ViewObservers instance for state access
            log_callback: Function to call for logging (e.g., self.log_message)
        """
        self.song = song_accessor
        self.application = application
        self.observers = observers
        self.log_message = log_callback

    def register_commands(self):
        """Register all command handlers

        Commands are categorized:
        - Direct: Can execute immediately without thread switching (read-only, no self.song())
        - Threaded: Must execute in main thread (accesses self.song())
        """
        return {
            "GET_VIEW": self._handle_get_view,           # Direct - no self.song() access
            "GET_STATE": self._handle_get_state,         # Threaded - needs self.song().is_playing
            "GET_PROJECT_PATH": self._handle_get_project_path,  # Direct - application property
            "EXPORT_XML": self._handle_export_xml,       # Threaded - saves the project as XML (requires project_path param)
            "SCROLL_TO_TOP": self._handle_scroll_to_top,
            "SCROLL_TO_BOTTOM": self._handle_scroll_to_bottom,
            "JUMP_TO_FIRST": self._handle_jump_to_first,  # Smart command - auto-detects view
            "JUMP_TO_LAST": self._handle_jump_to_last,    # Smart command - auto-detects view
        }

    def get_direct_commands(self):
        """Commands that can execute immediately without thread switching"""
        return {"GET_VIEW", "GET_PROJECT_PATH"}

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

    def _handle_get_project_path(self, params=None):
        """Handle GET_PROJECT_PATH command"""
        try:
            # Try multiple methods to get the project path
            path = None

            # Method 1: Try application.get_document()
            try:
                document = self.application.get_document()
                if document and hasattr(document, 'path') and document.path:
                    path = str(document.path)
                    self.log_message(f"Method 1 (get_document): Found path: {path}")
            except Exception as e:
                self.log_message(f"Method 1 (get_document) failed: {str(e)}")

            # Method 2: Try song().canonical_parent
            if not path:
                try:
                    song = self.song()
                    if hasattr(song, 'canonical_parent') and song.canonical_parent:
                        canonical = song.canonical_parent
                        if hasattr(canonical, 'canonical_parent') and canonical.canonical_parent:
                            path = str(canonical.canonical_parent)
                            self.log_message(f"Method 2 (canonical_parent): Found path: {path}")
                except Exception as e:
                    self.log_message(f"Method 2 (canonical_parent) failed: {str(e)}")

            # Method 3: Check if song has path attribute directly
            if not path:
                try:
                    song = self.song()
                    if hasattr(song, 'path') and song.path:
                        path = str(song.path)
                        self.log_message(f"Method 3 (song.path): Found path: {path}")
                except Exception as e:
                    self.log_message(f"Method 3 (song.path) failed: {str(e)}")

            if path:
                return {
                    "project_path": path
                }
            else:
                self.log_message("All methods failed - no document or path available")
                return {
                    "project_path": None
                }
        except Exception as e:
            self.log_message(f"Failed to get project path: {str(e)}")
            return {
                "project_path": None,
                "error": str(e)
            }

    def _handle_export_xml(self, params=None):
        """Handle EXPORT_XML command - exports project as XML to .vimabl directory

        Args:
            params: list with optional project path as first element (colon-delimited format).
                    If provided, uses that path directly.
                    If not provided, attempts to detect the path from the Live API.
        """
        try:
            import os

            # Check if project_path was provided as a parameter (colon-delimited format: EXPORT_XML:path)
            project_path = None
            if params and isinstance(params, list) and len(params) > 0:
                project_path = params[0]
                self.log_message(f"Export: Using provided project path: {project_path}")

            # If no path provided, try multiple methods to detect it
            if not project_path:
                self.log_message("Export: No project path provided, attempting auto-detection...")

                # Method 1: Try application.get_document()
                try:
                    document = self.application.get_document()
                    if document and hasattr(document, 'path') and document.path:
                        project_path = str(document.path)
                        self.log_message(f"Export: Method 1 (get_document) found path: {project_path}")
                except Exception as e:
                    self.log_message(f"Export: Method 1 (get_document) failed: {str(e)}")

                # Method 2: Try song().canonical_parent
                if not project_path:
                    try:
                        song = self.song()
                        if hasattr(song, 'canonical_parent') and song.canonical_parent:
                            canonical = song.canonical_parent
                            if hasattr(canonical, 'canonical_parent') and canonical.canonical_parent:
                                project_path = str(canonical.canonical_parent)
                                self.log_message(f"Export: Method 2 (canonical_parent) found path: {project_path}")
                    except Exception as e:
                        self.log_message(f"Export: Method 2 (canonical_parent) failed: {str(e)}")

                # Method 3: Check if song has path attribute directly
                if not project_path:
                    try:
                        song = self.song()
                        if hasattr(song, 'path') and song.path:
                            project_path = str(song.path)
                            self.log_message(f"Export: Method 3 (song.path) found path: {project_path}")
                    except Exception as e:
                        self.log_message(f"Export: Method 3 (song.path) failed: {str(e)}")

            # If no path found, return error
            if not project_path:
                self.log_message("Cannot export XML: project not saved or path not available")
                return {
                    "success": False,
                    "error": "Project must be saved before exporting XML"
                }

            # Extract project directory and name
            project_dir = os.path.dirname(project_path)
            project_name = os.path.splitext(os.path.basename(project_path))[0]

            # Create .vimabl directory
            vimabl_dir = os.path.join(project_dir, ".vimabl")
            if not os.path.exists(vimabl_dir):
                os.makedirs(vimabl_dir)
                self.log_message(f"Created .vimabl directory: {vimabl_dir}")

            # Extract XML from .als file (which is gzipped XML)
            # .als files are just gzipped XML, so we decompress them
            import gzip
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
