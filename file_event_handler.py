import numpy as np
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
        enc_remote_file_list = self.servercoms.get_file_list()
        relative_path_list_with_nonces = self.file_crypt.decrypt_file_list(enc_remote_file_list)  # TODO: There has got to be a better way!
        relative_path_list = list(np.array(relative_path_list_with_nonces)[:, 0])
        if relative_path not in relative_path_list:
            raise NotImplemented
        else:
            idx = list(np.array(relative_path_list_with_nonces)[:, 0]).index(relative_path)
        enc_file_name = self.file_crypt.encrypt_relative_file_path(relative_path, relative_path_list_with_nonces[idx][1])
        self.servercoms.register_deletion_of_file(enc_file_name)