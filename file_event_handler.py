import pathlib as pl
import time

from watchdog.events import FileSystemEventHandler

from resources import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, client):
        self.client = client
        self.new_files = {}

    def on_any_event(self, event):
        """Print any received event to console"""
        #print(f'event type: {event.event_type}  path : {event.src_path}')
        pass

    def on_created(self, event):
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

    def on_deleted(self, event):
        abs_path = pl.Path(event.src_path)
        if abs_path.is_dir() or abs_path.name.startswith(".goutputstream-"):
            return
        relative_path = abs_path.relative_to(globals.WORK_DIR)
        print("File deleted: " + str(relative_path))
        self.client.delete_remote_file(relative_path)  # ToDO: does not work on multi-delete ?

    def on_modified(self, event):
        cur_time = time.time()
        file_path = pl.Path(event.src_path)
        if file_path.is_dir() or file_path.name.startswith(".goutputstream-"):
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
        file_name_nonce = [fio.nonce for fio in globals.SERVER_FILE_DICT.values() if fio.path == relative_file_path]
        if len(file_name_nonce) != 1:
            print("How could this happen D: ??")
            error_message = f'Number of nonces match is not 1: {file_name_nonce}'
            raise NotImplementedError(error_message)
        file_name_nonce = file_name_nonce[0]
        self.client.send_file(file_path, file_name_nonce=file_name_nonce)

    def on_moved(self, event):
        file_path = pl.Path(event.src_path)
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        print("File moved:", str(relative_file_path))
        print("Not implemented!!")

    # Todo: on_ rename file ?? (move event ??) (Saving file on unix can be a move event)
    # TODO: Deleting folders.
    # TODO: Delete doesn't work all the time.
    # TODO: CLI's cmd 'df _' on only local.
    # TODO: Fix get_file - Make observers turn off temporarily.
