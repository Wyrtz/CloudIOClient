import pathlib as pl

from watchdog.events import FileSystemEventHandler

from resources import globals
from security.filecryptography import FileCryptography


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, file_crypt: FileCryptography, client):
        self.file_crypt = file_crypt
        self.client = client

    def on_any_event(self, event):
        """Print any received event to console"""
        # print(f'event type: {event.event_type}  path : {event.src_path}')
        pass

    def on_created(self, event):
        """Send newly created file to the server"""
        file_path = pl.Path(event.src_path)
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        print("File created: " + str(relative_file_path))
        if relative_file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(relative_file_path)
            return
        self.client.send_file(file_path)

    def on_deleted(self, event):
        abs_path = pl.Path(event.src_path)
        relative_path = abs_path.relative_to(globals.WORK_DIR)
        print("File deleted: " + str(relative_path))
        server_file_list = globals.SERVER_FILE_LIST
        self.client.delete_remote_file(relative_path)
