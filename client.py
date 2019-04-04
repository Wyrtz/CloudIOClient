import os
import pathlib as pl
from threading import Thread
from time import sleep
from watchdog.events import FileSystemEventHandler
from ServerComs import ServComs
from filecryptography import FileCryptography
from folder_watcher import folder_watcher
import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    # ToDo: handle creations properly.

    def __init__(self, servercoms, file_crypt):
        self.servercoms = servercoms
        self.file_crypt = file_crypt

    def on_any_event(self, event):
        """Print any received event to console"""
        print(f'event type: {event.event_type}  path : {event.src_path}')

    def on_created(self, event):
        """Send newly created file to the server"""
        file_name = event.src_path.split("/")[1]
        response = None
        enc_file_name = ""
        file_path = pl.PurePath.joinpath(globals.FILE_FOLDER, file_name)
        if file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(file_path)
            print("Removed ", file_path, "from queue")
            return
        try:
            enc_file_name, additional_data = self.file_crypt.encrypt_file(file_path)
            response = self.servercoms.send_file(enc_file_name, additional_data)
        except PermissionError:
            print("failed once")
            sleep(5)
            self.on_created(event)
            return
        if response.status_code == 200:
            pl.Path.unlink(enc_file_name) # Delete file
        # print("Send file")
        # sleep(3)
        # print("Delete file")
        # os.remove(file_path)
        # sleep(3)
        # print("Get file")
        # _, enc_file_path = self.servercoms.get_file(enc_file_name)
        # dec_file_path = self.file_crypt.decrypt_file(enc_file_path)


class client():

    def __init__(self, serverIP, file_folder=globals.FILE_FOLDER):
        self.serverIP = serverIP
        self.file_folder = file_folder
        self.servercoms = ServComs(serverIP)
        self.file_crypt = FileCryptography()
        self.handler = MyHandler(self.servercoms, self.file_crypt)
        folder_watcher_thread = Thread(target=folder_watcher, args=(file_folder, self.handler))
        folder_watcher_thread.start()
        # self.folder_watcher = folder_watcher(folder + "/", self.handler)
        # self.sync_files()

    def get_file(self, file_name):
        # Encrypt the name, send a request and get back either '404' or a file candidate.
        # If the candidate is valid and newer, keep it.
        enc_file_name = FileCryptography.encrypt_filename(file_name)
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


if __name__ == "__main__":
    serverIP = 'wyrnas.myqnapcloud.com:8000'
    globals.create_folders()
    client = client(serverIP)
