"""
Socket server and thread synchronization for command execution
"""

import socket
import threading
import json


class CommandServer:
    """Manages socket server and thread-safe command execution"""

    def __init__(self, command_handlers, schedule_callback, log_callback, host='127.0.0.1', port=9001):
        """Initialize command server

        Args:
            command_handlers: CommandHandlers instance
            schedule_callback: Function to schedule work in main thread (e.g., self.schedule_message)
            log_callback: Function to call for logging (e.g., self.log_message)
            host: Server host address
            port: Server port
        """
        self.command_handlers = command_handlers
        self.schedule_message = schedule_callback
        self.log_message = log_callback
        self.host = host
        self.port = port

        # Thread-safe command execution
        self._pending_command = None
        self._command_result = None
        self._command_lock = threading.Lock()
        self._result_ready = threading.Event()

        # Get command registry
        self._handlers = command_handlers.register_commands()
        self._direct_commands = command_handlers.get_direct_commands()

        # Server thread
        self._server_thread = None

    def start(self):
        """Start the server in a background thread"""
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        self.log_message(f"Command server started on {self.host}:{self.port}")

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

    def _run_server(self):
        """Run a simple socket server to expose state to Hammerspoon"""
        # Outer try-catch for server setup only
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, self.port))
                s.listen(1)
                self.log_message(f"Server listening on {self.host}:{self.port}")

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
                                handler = self._handlers.get(command)
                                if handler:
                                    try:
                                        # Check if command can execute directly (no thread switching)
                                        if command in self._direct_commands:
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
