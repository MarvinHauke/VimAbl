"""
Observer setup and callbacks for Live view changes
"""


class ViewObservers:
    """Manages observers for Live's view changes"""

    def __init__(self, application, log_callback):
        """Initialize observers

        Args:
            application: Live.Application instance
            log_callback: Function to call for logging (e.g., self.log_message)
        """
        self.application = application
        self.log_message = log_callback

        # State tracking
        self.current_view = "session"  # Default to session view
        self.browser_visible = False
        self.device_visible = False
        self.clip_view_visible = False
        self.detail_view = "device"  # "device" or "clip"
        self.groove_pool_visible = False
        self.info_view_visible = False

    def setup(self):
        """Setup observers for view changes"""
        view = self.application.view

        # Add observers for view changes (with error handling for duplicates)
        self._add_observer(view, "Session", self._on_view_changed)
        self._add_observer(view, "Arranger", self._on_view_changed)
        self._add_observer(view, "Browser", self._on_browser_changed)
        self._add_observer(view, "Detail", self._on_device_changed)
        self._add_observer(view, "Detail/DeviceChain", self._on_device_changed)
        self._add_observer(view, "Detail/Clip", self._on_clip_changed)
        self._add_observer(view, "GroovePool", self._on_groove_pool_changed)
        self._add_observer(view, "Help", self._on_info_view_changed)

    def _add_observer(self, view, view_name, callback):
        """Add an observer with error handling for duplicates"""
        try:
            view.add_is_view_visible_listener(view_name, callback)
        except RuntimeError:
            pass  # Observer already connected

    def teardown(self):
        """Remove all observers"""
        view = self.application.view

        self._remove_observer(view, "Session", self._on_view_changed)
        self._remove_observer(view, "Arranger", self._on_view_changed)
        self._remove_observer(view, "Browser", self._on_browser_changed)
        self._remove_observer(view, "Detail", self._on_device_changed)
        self._remove_observer(view, "Detail/DeviceChain", self._on_device_changed)
        self._remove_observer(view, "Detail/Clip", self._on_clip_changed)
        self._remove_observer(view, "GroovePool", self._on_groove_pool_changed)
        self._remove_observer(view, "Help", self._on_info_view_changed)

    def _remove_observer(self, view, view_name, callback):
        """Remove an observer with error handling"""
        try:
            view.remove_is_view_visible_listener(view_name, callback)
        except RuntimeError:
            pass

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

    def get_state(self):
        """Get current state dictionary"""
        return {
            "view": self.current_view,
            "browser_visible": self.browser_visible,
            "device_visible": self.device_visible,
            "clip_view_visible": self.clip_view_visible,
            "detail_view": self.detail_view,
            "groove_pool_visible": self.groove_pool_visible,
            "info_view_visible": self.info_view_visible
        }
