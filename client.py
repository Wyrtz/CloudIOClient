import os
import pathlib as pl
from threading import Thread
from time import sleep
from ServerComs import ServComs
from security import keyderivation
from security.filecryptography import FileCryptography
from file_event_handler import MyHandler
from watchdog.observers import Observer
from resources import globals


class Client:

    def __init__(self, username, password, server_location=globals.SERVER_LOCATION, file_folder=globals.FILE_FOLDER):
        self.server_location = server_location
        self.file_folder = file_folder
        self.servercoms = ServComs(server_location)
        self.kd = keyderivation.KeyDerivation(username)  # TODO: Username?
        if self.kd.has_password():
            self.file_crypt = FileCryptography(self.kd.derive_key(password))
        else:
            self.file_crypt = self.kd.select_first_pw(password)
        self.handler_thread = Thread(target=MyHandler, args=(self.servercoms, self.file_crypt, self))
        self.handler_thread.start()
        # Start initial folder observer
        self.observers_list = []
        self.start_observing()

    def start_observing(self):
        self.start_new_folder_observer(self.file_folder)

    def start_new_folder_observer(self, file_folder_path):
        new_observer = Observer()
        handler = MyHandler(self.servercoms, self.file_crypt, self)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def send_file(self, file_path):
        try:
            enc_file_path, additional_data = self.file_crypt.encrypt_file(
                file_path, globals.get_nonce(), globals.get_nonce()
            )
            success = self.servercoms.send_file(enc_file_path, additional_data)
        except PermissionError:
            print("Unable to send file immediately...")
            sleep(1)
            self.send_file(file_path)
            return
        pl.Path.unlink(enc_file_path)  # Delete file
        if success:
            print("File", file_path.stem, "send successfully!")
        # ToDo: handle fail ?

    def get_file(self, file_name):
        """Encrypt the name, send a request and get back either '404' or a file candidate.
           If the candidate is valid and newer, keep it."""
        globals.DOWNLOADED_FILE_QUEUE.append(file_name)
        # TODO: implement get_nonce_of_filename(name)
        enc_file_name = self.file_crypt.encrypt_relative_file_path(file_name, nonce)
        try:
            tmp_enc_file_path, additional_data = self.servercoms.get_file(str(enc_file_name))
        except FileNotFoundError:
            print("File not found on server.")
            return
        self.file_crypt.decrypt_file(tmp_enc_file_path,  # TODO: If doesn't validate, does it overwrite?
                                     additional_data=additional_data)
        pl.Path.unlink(tmp_enc_file_path)

    def delete_file(self, file_name: pl.Path):
        enc_path = self.file_crypt.encrypt_relative_file_path(file_name)
        self.servercoms.register_deletion_of_file(enc_path)

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        # ToDo: recursive (folders)
        # ToDO: PathLib? No os.listdir function
        file_list = os.listdir(self.file_folder)
        file_list = [pl.Path(x) for x in file_list]
        file_list = [pl.Path.joinpath(globals.FILE_FOLDER, x) for x in file_list]
        file_list = [x.relative_to(globals.WORK_DIR) for x in file_list]
        return file_list

    def sync_files(self):  # TODO: Refactor this.
        local_file_list = self.get_local_file_list()
        enc_remote_file_list = self.servercoms.get_file_list()
        dec_remote_file_list = self.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x) for x in dec_remote_file_list]
        files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list)
        files_not_on_client = globals.get_list_difference(pathlib_remote_file_list, local_file_list)
        for file in files_not_on_server:
            abs_path = pl.Path.joinpath(globals.WORK_DIR, file)
            self.send_file(abs_path)
        for file in files_not_on_client:
            self.get_file(file)

    def close_client(self):
        """Close all observers observing a folder"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()
