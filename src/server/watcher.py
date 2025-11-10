"""
File watcher for monitoring changes to Ableton Live project files.

This module provides:
- Filesystem monitoring for .als files
- Change detection and notification
- Integration with AST server for automatic reloading
"""

import time
from pathlib import Path
from typing import Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class AbletonFileHandler(FileSystemEventHandler):
    """
    File system event handler for Ableton Live files.

    Monitors .als and .xml files and triggers callbacks on changes.
    """

    def __init__(self, callback: Callable[[Path], None], extensions: Set[str] = {".als", ".xml"}):
        """
        Initialize the file handler.

        Args:
            callback: Function to call when a file changes
            extensions: Set of file extensions to monitor
        """
        self.callback = callback
        self.extensions = extensions
        self.last_modified = {}
        self.debounce_seconds = 1.0  # Ignore duplicate events within 1 second

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process files with relevant extensions
        if file_path.suffix not in self.extensions:
            return

        # Debounce: ignore if we just processed this file
        now = time.time()
        last_time = self.last_modified.get(file_path, 0)
        if now - last_time < self.debounce_seconds:
            return

        self.last_modified[file_path] = now

        # Trigger callback
        try:
            self.callback(file_path)
        except Exception as e:
            print(f"Error processing file change: {e}")


class FileWatcher:
    """
    Watches a directory (or file) for changes to Ableton Live projects.

    Usage:
        def on_change(file_path):
            print(f"Project changed: {file_path}")

        watcher = FileWatcher(on_change)
        watcher.watch("/path/to/projects")
        watcher.start()

        # Later...
        watcher.stop()
    """

    def __init__(self, callback: Callable[[Path], None]):
        """
        Initialize the file watcher.

        Args:
            callback: Function to call when a file changes (receives Path object)
        """
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.handler = AbletonFileHandler(callback)
        self.watch_path: Optional[Path] = None

    def watch(self, path: Path) -> None:
        """
        Set the path to watch.

        Args:
            path: Directory or file to watch
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        # If it's a file, watch its parent directory
        if path.is_file():
            self.watch_path = path.parent
        else:
            self.watch_path = path

    def start(self) -> None:
        """Start watching for file changes."""
        if not self.watch_path:
            raise RuntimeError("No watch path set. Call watch() first.")

        if self.observer and self.observer.is_alive():
            raise RuntimeError("Watcher is already running")

        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_path), recursive=True)
        self.observer.start()
        print(f"Watching for changes in: {self.watch_path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("File watcher stopped")

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self.observer is not None and self.observer.is_alive()

    def __enter__(self):
        """Context manager support."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.stop()


# Example usage and integration with AST server
if __name__ == "__main__":
    from .api import ASTServer

    server = ASTServer()

    def on_project_change(file_path: Path):
        """Reload project when it changes."""
        print(f"\nProject file changed: {file_path}")
        try:
            result = server.load_project(file_path)
            print(f"Reloaded project: {result}")
            info = server.get_project_info()
            print(f"Project info: {info}")
        except Exception as e:
            print(f"Error reloading project: {e}")

    # Watch a project file
    project_path = Path("Example_Project/example.als")
    if project_path.exists():
        # Initial load
        server.load_project(project_path)
        print(f"Initial load: {server.get_project_info()}")

        # Start watching
        watcher = FileWatcher(on_project_change)
        watcher.watch(project_path)
        watcher.start()

        try:
            print("Watching for changes... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping watcher...")
            watcher.stop()
