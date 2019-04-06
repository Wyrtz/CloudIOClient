import os
import pathlib as pl
from threading import Thread
from time import sleep, time
from watchdog.events import FileSystemEventHandler
from ServerComs import ServComs
from filecryptography import FileCryptography
from watchdog.observers import Observer
import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, servercoms: ServComs, file_crypt: FileCryptography):
        self.servercoms = servercoms
        self.file_crypt = file_crypt

    def on_any_event(self, event):
        """Print any received event to console"""
        print(f'event type: {event.event_type}  path : {event.src_path}')

    def on_created(self, event):
        """Send newly created file to the server"""
        file_path = pl.Path(event.src_path)
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        if relative_file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(relative_file_path)
            return
        try:
            enc_file_path, additional_data = self.file_crypt.encrypt_file(file_path)
            self.servercoms.send_file(enc_file_path, additional_data)
        except PermissionError:
            print("failed once")
            sleep(5)
            self.on_created(event)
            return
        # TODO: Handle httperror?
        pl.Path.unlink(enc_file_path)  # Delete file

    def on_deleted(self, event):
        abs_path = pl.Path(event.src_path)
        relative_path = abs_path.relative_to(globals.WORK_DIR)
        enc_file_name = self.file_crypt.encrypt_relative_file_path(relative_path)
        self.servercoms.register_deletion_of_file(enc_file_name)


class Client:

    def __init__(self, server_location=globals.SERVER_LOCATION, file_folder=globals.FILE_FOLDER):
        self.server_location = server_location
        self.file_folder = file_folder
        self.servercoms = ServComs(server_location)
        self.file_crypt = FileCryptography()
        self.handler_thread = Thread(target=MyHandler, args=(self.servercoms, self.file_crypt))
        self.handler_thread.start()
        # Start initial folder observer
        self.observers_list = []
        self.start_folder_observer(self.file_folder)

    def start_folder_observer(self, file_folder_path):
        new_observer = Observer()
        handler = MyHandler(self.servercoms, self.file_crypt)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def get_file(self, file_name):
        """Encrypt the name, send a request and get back either '404' or a file candidate.
           If the candidate is valid and newer, keep it."""
        enc_file_name = FileCryptography.encrypt_relative_file_path(file_name)
        try:
            tmp_enc_file_path, additional_data = self.servercoms.get_file(enc_file_name)
        except FileNotFoundError:
            print("File not found on server.")
            return
        self.file_crypt.decrypt_file(tmp_enc_file_path,  # TODO: If doesn't validate, does it overwrite?
                                     additional_data=additional_data)
        os.remove(tmp_enc_file_path)

    def get_folder_list(self):
        """Return a list where each element is the string name of this file"""
        # ToDo: recursive (folders)
        # ToDO: PathLib!
        files = os.listdir(self.folder)
        file_list = []
        for name in files:
            file_list.append(name)
        return file_list

    def sync_files(self):  # TODO: Refactor this.
        response = self.servercoms.get_file_list()
        server_files = list(response.json())
        client_files = self.get_folder_list()
        print("server files: ", server_files)
        print("client_files", client_files)
        # for remote_file in server_files:
        #     if remote_file not in client_files:
        #         self.servercoms.get_file(remote_file)
        # todo: FINNISH THIS!
        # todo: Test this!
        # todo: handle file not found, no connection etc. !

    def close_client(self):
        """Close all observers observing a folder"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()


if __name__ == "__main__":
    serverIP = 'wyrnas.myqnapcloud.com:8000'
    client = Client(serverIP)
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        client.close_client()

