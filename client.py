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
# TODO: Should be able to use old encrypted keys.
# TODO: Modified files.
# TODO: Can recover files under old password.

class Client:

    def __init__(self, username, password, server_location=globals.SERVER_LOCATION, file_folder=globals.FILE_FOLDER):
        self.server_location = server_location
        self.file_folder = file_folder
        self.servercoms = ServComs(server_location)
        self.kd = keyderivation.KeyDerivation(username)
        if self.kd.has_password():
            self.file_crypt = FileCryptography(self.kd.derive_key(password))
        else:
            raise AssertionError  # Handled by CLI now.
        globals.SERVER_FILE_LIST = self.file_crypt.decrypt_file_list_extended(self.servercoms.get_file_list())
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

    def send_file(self, file_path):  # TODO: Not handling file modification when name nonce should be constant.
        try:
            file_name_nonce = globals.get_nonce()
            file_data_nonce = globals.get_nonce()
            enc_file_path, additional_data = self.file_crypt.encrypt_file(
                file_path, file_name_nonce, file_data_nonce
            )
            success = self.servercoms.send_file(enc_file_path, additional_data)
        except PermissionError:
            print("Unable to send file immediately...")
            sleep(1)
            self.send_file(file_path)
            return
        pl.Path.unlink(enc_file_path)  # Delete file
        relative_path = file_path.relative_to(globals.WORK_DIR)
        relative_enc_path = enc_file_path.relative_to(globals.TEMPORARY_FOLDER)
        if success:  # TODO: Check if redundant; see servercoms
            print("File", file_path.stem, "send successfully!")
            globals.SERVER_FILE_LIST.append([relative_path, file_name_nonce, relative_enc_path])

    def get_file(self, file_name):
        """Encrypt the name, send a request and get back either '404' or a file candidate.
           If the candidate is valid and newer, keep it."""
        globals.DOWNLOADED_FILE_QUEUE.append(file_name)
        enc_file_name_list = [lst[2] for lst in globals.SERVER_FILE_LIST if lst[0] == file_name]
        if len(enc_file_name_list) != 1:
            raise NotImplementedError("Zero, two or more files on server derived from the same name", enc_file_name_list)
        try:
            tmp_enc_file_path, additional_data = self.servercoms.get_file(str(enc_file_name_list[0]))
        except FileNotFoundError:
            print("File not found on server.")
            return
        self.file_crypt.decrypt_file(tmp_enc_file_path, additional_data=additional_data)
        pl.Path.unlink(tmp_enc_file_path)

    def delete_remote_file(self, file_name: pl.Path):
        server_file_list = globals.SERVER_FILE_LIST
        enc_path_lst = [lst[2] for lst in server_file_list if lst[0] == file_name]
        if len(enc_path_lst) != 1:
            raise NotImplemented
        self.servercoms.register_deletion_of_file(enc_path_lst[0])

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        # ToDo: recursive (folders)
        file_list = os.listdir(self.file_folder)
        file_list = [pl.Path(x) for x in file_list]
        file_list = [pl.Path.joinpath(globals.FILE_FOLDER, x) for x in file_list]
        file_list = [x.relative_to(globals.WORK_DIR) for x in file_list]
        return file_list

    def sync_files(self):
        local_file_list = self.get_local_file_list()
        enc_remote_file_list_with_nonces = self.servercoms.get_file_list()
        globals.SERVER_FILE_LIST = self.file_crypt.decrypt_file_list_extended(enc_remote_file_list_with_nonces)
        remote_file_list = [lst[0] for lst in globals.SERVER_FILE_LIST]
        files_not_on_server = globals.get_list_difference(local_file_list, remote_file_list)
        files_not_on_client = globals.get_list_difference(remote_file_list, local_file_list)
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
