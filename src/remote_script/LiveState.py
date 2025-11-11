"""
Main Remote Script controller that observes Live's state
"""

import Live
from _Framework.ControlSurface import ControlSurface

from .observers import ViewObservers
from .commands import CommandHandlers
from .server import CommandServer


class LiveState(ControlSurface):
    """Observes Live state and exposes it via a local socket server"""

    def __init__(self, c_instance):
        super().__init__(c_instance)

        self.application = Live.Application.get_application()

        # Initialize observers
        self.observers = ViewObservers(self.application, self.log_message)
        self.observers.setup()

        # Initialize command handlers
        self.command_handlers = CommandHandlers(
            song_accessor=self.song,
            application=self.application,
            observers=self.observers,
            log_callback=self.log_message
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

        self.log_message("Live State Remote Script initialized")

    def _setup_document_listener(self):
        """Set up listener for document path changes"""
        try:
            document = self.application.get_document()
            if document and hasattr(document, 'add_path_listener'):
                document.add_path_listener(self._on_document_path_changed)
                self.log_message("Document path listener added")
        except Exception as e:
            self.log_message(f"Failed to add document listener: {str(e)}")

    def _on_document_path_changed(self):
        """Called when the document path changes (e.g., after Save As or first save)"""
        try:
            document = self.application.get_document()
            if document and document.path:
                path = str(document.path)
                self.log_message(f"Document path changed to: {path}")
                # Broadcast the path change via the server
                # This allows Hammerspoon/WebSocket to react to the save
                self.server.broadcast_event("PROJECT_PATH_CHANGED", {"project_path": path})
        except Exception as e:
            self.log_message(f"Error in document path listener: {str(e)}")

    def disconnect(self):
        """Called when script is disconnected"""
        self.log_message("Live State Remote Script disconnecting")

        # Remove observers
        self.observers.teardown()

        super().disconnect()
