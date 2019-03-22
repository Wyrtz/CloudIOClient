import time
from watchdog.observers import Observer


class folder_watcher:
    """Watches a folder."""

    def __init__(self, path, handler):
        """Initialise the folder_watcher with what folder to watch, and who to call (handle) when an event occures"""
        self.path = path
        event_handler = handler
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


