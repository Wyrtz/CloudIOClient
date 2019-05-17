import pathlib as pl
import platform
import time
import os

from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileDeletedEvent, DirDeletedEvent

from resources import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, client):
        self.client = client
        self.new_files = {}

    def on_any_event(self, event: FileSystemEvent):
        """Print any received event to console"""
        #print(f'event type: {event.event_type}  path : {event.src_path}')
        pass

    def on_created(self, event: FileSystemEvent):
        """Send newly created file to the server"""
        file_path = pl.Path(event.src_path)
        if file_path.is_dir() or file_path.name.startswith(".goutputstream-"):
            return
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        print("File created: " + str(relative_file_path))
        if relative_file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(relative_file_path)
            return
        self.new_files[relative_file_path] = time.time()
        self.client.send_file(file_path)

    def on_deleted(self, event: FileSystemEvent):
        abs_path = pl.Path(event.src_path)
        if isinstance(event, DirDeletedEvent) or (platform.system() == "Windows" and abs_path.suffix == ""):
            server_dict_copy = globals.SERVER_FILE_DICT.copy()
            for filePath in server_dict_copy.keys():
                try:
                    rel_path = pl.Path.relative_to(abs_path, globals.WORK_DIR)
                    filePath.relative_to(rel_path)
                    self.client.delete_remote_file(filePath)
                except ValueError:
                    pass
        if abs_path.name.startswith(".goutputstream-"):
            return
        relative_path = abs_path.relative_to(globals.WORK_DIR)
        self.client.delete_remote_file(relative_path)

    def on_modified(self, event: FileSystemEvent):
        cur_time = time.time()
        file_path = pl.Path(event.src_path)
        if file_path.is_dir() or not file_path.is_file() or file_path.name.startswith(".goutputstream-"):
            return
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        if relative_file_path in self.new_files:
            time_of_create = self.new_files.get(relative_file_path)
            if not cur_time - time_of_create > 1:  # Ensure it is not the modify event from the create event
                return
            else:  # Clean up in the dict
                self.new_files.pop(relative_file_path)
        print("File modified:" + str(relative_file_path))
        # Get the nonce used for the filename such that the filename stays the same:
        fio = globals.SERVER_FILE_DICT.get(relative_file_path, None)
        if not fio:  # File not on server yet
            file_name_nonce = globals.generate_random_nonce()
        else:
            file_name_nonce = fio.nonce
        self.client.send_file(file_path, file_name_nonce=file_name_nonce)

    def on_moved(self, event: FileSystemEvent):
        file_path = pl.Path(event.src_path)
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        print("File moved:", str(relative_file_path))
        print("Not implemented!!")

    # Todo: on_ rename file ?? (move event ??) (Saving file on unix can be a move event)
    # TODO: CLI's cmd 'df _' on only local.
    # TODO: Fix get_file - Make observers turn off temporarily.
