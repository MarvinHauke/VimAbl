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

        self.log_message("Live State Remote Script initialized")

    def disconnect(self):
        """Called when script is disconnected"""
        self.log_message("Live State Remote Script disconnecting")

        # Remove observers
        self.observers.teardown()

        super().disconnect()
