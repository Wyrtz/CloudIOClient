from watchdog.events import FileSystemEventHandler

from ServerComs import ServComs
from security.filecryptography import FileCryptography
import pathlib as pl
from resources import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, servercoms: ServComs, file_crypt: FileCryptography, client):
        self.servercoms = servercoms
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
        enc_name_list = [lst[2] for lst in server_file_list if lst[0] == relative_path]
        for enc_name in enc_name_list:
            self.servercoms.register_deletion_of_file(enc_name)