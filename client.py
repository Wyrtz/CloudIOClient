import pathlib as pl
from hashlib import sha3_224
from time import sleep

from watchdog.observers import Observer

from ServerComs import ServComs
from file_event_handler import MyHandler
from resources import globals
from security import keyderivation, secretsharing, filecryptography
from security.filecryptography import FileCryptography


# TODO: Should be able to use old encrypted keys.
# TODO: Can recover files under old password.


def hash_key_to_userID(key):
    hasher = sha3_224()
    hasher.update(bytes("Keyhash", 'utf-8'))
    hasher.update(key)
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
        self.file_crypt_dict = {"default": self.file_crypt}
        self.userID = hash_key_to_userID(key)
        self.servercoms = ServComs(server_location, self.userID)
        self.file_crypt.update_local_server_file_list(self.servercoms.get_file_list())
        self.observers_list = []
        self.start_observing()

    def start_observing(self):
        self.start_new_folder_observer(self.file_folder)

    def start_new_folder_observer(self, file_folder_path):
        new_observer = Observer()
        handler = MyHandler(self)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def send_file(self, file_path, file_name_nonce=globals.get_nonce()):
        file_crypt = self.get_file_crypt(file_path)
        try:
            file_data_nonce = globals.get_nonce()  # Unique
            enc_file_path, additional_data = file_crypt.encrypt_file(
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
            fio = globals.FileInfo(relative_path, file_name_nonce, relative_enc_path, file_path.stat().st_mtime)
            globals.SERVER_FILE_DICT[fio.path] = fio

    def get_file(self, file_name):
        """Encrypt the name, send a request and get back either '404' or a file candidate.
           If the candidate is valid and newer, keep it."""
        file_crypt = self.get_file_crypt(file_name)
        globals.DOWNLOADED_FILE_QUEUE.append(file_name)
        enc_file_name_list = [fio.enc_path for fio in globals.SERVER_FILE_DICT.values() if fio.path == file_name]
        if len(enc_file_name_list) != 1:
            raise NotImplementedError("Zero, two or more files on server derived from the same name", enc_file_name_list)
        try:
            tmp_enc_file_path, additional_data = self.servercoms.get_file(str(enc_file_name_list[0]))
        except FileNotFoundError:
            print("File not found on server.")
            return
        file_crypt.decrypt_file(tmp_enc_file_path, additional_data=additional_data)
        pl.Path.unlink(tmp_enc_file_path)

    def delete_remote_file(self, file_rel_path: pl.Path):
        enc_path_lst = [fio.enc_path for fio in globals.SERVER_FILE_DICT.values() if fio.path == file_rel_path]
        if len(enc_path_lst) != 1:
            raise NotImplementedError(f"List is not 1 long! Contains: {enc_path_lst}")
        globals.SERVER_FILE_DICT.pop(file_rel_path)
        self.servercoms.register_deletion_of_file(enc_path_lst[0])

    def get_file_crypt(self, path: pl.Path) -> FileCryptography:
        path = path.absolute()
        relative_path = path.relative_to(globals.WORK_DIR)
        file_crypt = self.file_crypt_dict.get(relative_path, self.file_crypt_dict.get("default"))
        return file_crypt

    def update_server_file_list(self):
        """Get the filelist from server, decrypt and set globals server file list"""
        server_file_list = self.servercoms.get_file_list()
        self.file_crypt.update_local_server_file_list(server_file_list)

    def create_shared_folder(self, folder_name: pl.Path, key):
        folder_path = folder_name.absolute()
        folder_path.mkdir()
        file_crypt = FileCryptography(key)
        self.file_crypt_dict[folder_name] = file_crypt
        return secretsharing.split_secret(key, 1, 1)

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        file_list = [i.relative_to(globals.WORK_DIR) for i in globals.FILE_FOLDER.glob("**/*.*")]
        return file_list

    def sync_files(self, sync_dict):
        self.close_observers()
        for key in sync_dict:
            c_time, s_time = sync_dict.get(key)
            key = pl.Path.joinpath(globals.WORK_DIR, key)
            if c_time < s_time:  # Server has the newest version
                # Send and delete file locally, such that the client can recover it if needed
                if key.exists():
                    self.send_file(key)
                    key.unlink()
                rel_key = key.relative_to(globals.WORK_DIR)
                self.get_file(rel_key)
            elif c_time > s_time:  # Client has the newest version
                self.send_file(key)
        self.start_observing()

    def close_observers(self):
        """Close all observers observing a folder"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()
        return

    def backup_key(self, password, required_share_amount_to_recover: int, share_amount: int) -> list:
        key = self.kd.derive_key(password)
        return secretsharing.split_secret(key, required_share_amount_to_recover - 1, share_amount)

    def add_key_from_shares(self, shares: list):
        key = secretsharing.recover_secret(shares)
        # Todo: encrypt this key under our existing key and save it
        # Todo: How to map ? UserID -> key ? Folder -> key ? third?


def replace_key_from_backup(shares, username, new_pw):
    key = secretsharing.recover_secret(shares)
    keyderivation.KeyDerivation(username).replace_pw_from_key(key, new_pw)
