import os
import pathlib as pl
from threading import Thread
from time import sleep

from hashlib import sha3_224

from ServerComs import ServComs
from security import keyderivation
from security.filecryptography import FileCryptography
from file_event_handler import MyHandler
from watchdog.observers import Observer
from resources import globals
# TODO: Should be able to use old encrypted keys.
# TODO: Can recover files under old password.


def hash_key_to_userID(key):
    hasher = sha3_224()
    hasher.update(bytes("Keyhash", 'utf-8'))
    hasher.update(bytes.fromhex(key))
    return hasher.digest().hex()


class Client:

    def __init__(self, username, password, server_location=globals.SERVER_LOCATION, file_folder=globals.FILE_FOLDER):
        self.server_location = server_location
        self.file_folder = file_folder
        self.kd = keyderivation.KeyDerivation(username)
        if self.kd.has_password():
            key = self.kd.derive_key(password)
            self.file_crypt = FileCryptography(key)
        else:
            raise AssertionError  # Handled by CLI now.
        self.userID = hash_key_to_userID(key)
        self.servercoms = ServComs(server_location, self.userID)
        globals.SERVER_FILE_LIST = self.file_crypt.decrypt_file_list_extended(self.servercoms.get_file_list())
        # self.handler_thread = Thread(target=MyHandler, args=(self.file_crypt, self))
        # self.handler_thread.start()
        # Start initial folder observer
        self.observers_list = []
        self.start_observing()

    def start_observing(self):
        self.start_new_folder_observer(self.file_folder)

    def start_new_folder_observer(self, file_folder_path):
        new_observer = Observer()
        handler = MyHandler(self.file_crypt, self)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def send_file(self, file_path, file_name_nonce=globals.get_nonce()):
        try:
            file_data_nonce = globals.get_nonce()  # Unique
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
            print("File\"" + file_path.stem + "\"send successfully!")
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
        enc_path_lst = [lst[2] for lst in globals.SERVER_FILE_LIST if lst[0] == file_name]
        if len(enc_path_lst) != 1:
            print("List is not 1 long! Contains:", enc_path_lst)
            raise NotImplementedError
        globals.SERVER_FILE_LIST = [lst for lst in globals.SERVER_FILE_LIST if lst[0] != file_name]
        self.servercoms.register_deletion_of_file(enc_path_lst[0])

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        # # ToDo: recursive (folders)
        # file_list = os.listdir(self.file_folder)
        # file_list = [pl.Path(x) for x in file_list]
        # file_list = [pl.Path.joinpath(globals.FILE_FOLDER, x) for x in file_list]
        # file_list = [x.relative_to(globals.WORK_DIR) for x in file_list]
        # return file_list
        file_list = [i.relative_to(globals.WORK_DIR) for i in globals.FILE_FOLDER.glob("**/*.*")]

        return file_list

    def sync_files(self):
        self.close_observers()
        globals.IS_SYNCING = True
        local_file_list = self.get_local_file_list()
        enc_remote_file_list_with_nonces_and_timestamp = self.servercoms.get_file_list()
        globals.SERVER_FILE_LIST = self.file_crypt.decrypt_file_list_extended(enc_remote_file_list_with_nonces_and_timestamp)
        remote_file_list = [lst[0] for lst in globals.SERVER_FILE_LIST]
        files_not_on_server = globals.get_list_difference(local_file_list, remote_file_list)
        files_not_on_client = globals.get_list_difference(remote_file_list, local_file_list)
        for file in files_not_on_server:
            abs_path = pl.Path.joinpath(globals.WORK_DIR, file)
            self.send_file(abs_path)
        for file in files_not_on_client:
            self.get_file(file)
        globals.IS_SYNCING = False
        self.start_observing()

    def close_observers(self):
        """Close all observers observing a folder"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()
        return
