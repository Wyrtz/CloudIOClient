import pathlib as pl
from hashlib import sha3_224
from time import sleep

from cryptography.exceptions import InvalidTag
from watchdog.observers import Observer

from ServerComs import ServComs
from file_event_handler import MyHandler
from resources import globals
from security import keyderivation, secretsharing
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
        self.userID = hash_key_to_userID(key)
        self.servercoms = ServComs(server_location, self.userID)
        self.folder_to_file_crypt_servercoms_dict = {"default": (self.file_crypt, self.servercoms)}
        self.update_server_file_list()
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
        file_crypt, servercoms = self.get_file_crypt_servercoms(file_path)
        try:
            file_data_nonce = globals.get_nonce()  # Unique
            enc_file_path, additional_data = file_crypt.encrypt_file(
                file_path, file_name_nonce, file_data_nonce
            )
            success = servercoms.send_file(enc_file_path, additional_data)
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
        file_crypt, servercoms = self.get_file_crypt_servercoms(file_name)
        globals.DOWNLOADED_FILE_QUEUE.append(file_name)
        enc_file_name_list = [fio.enc_path for fio in globals.SERVER_FILE_DICT.values() if fio.path == file_name]
        if len(enc_file_name_list) != 1:
            raise NotImplementedError("Zero, two or more files on server derived from the same name", enc_file_name_list)
        try:
            tmp_enc_file_path, additional_data = servercoms.get_file(str(enc_file_name_list[0]))
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

    def get_file_crypt_servercoms(self, path: pl.Path) -> (FileCryptography, ServComs):
        path = path.absolute()
        relative_path = path.relative_to(globals.WORK_DIR)
        file_crypt, servercoms = self.folder_to_file_crypt_servercoms_dict.get(relative_path, self.folder_to_file_crypt_servercoms_dict.get("default"))
        return file_crypt, servercoms

    def update_server_file_list(self):
        """Get the filelist from server, decrypt and set globals server file list"""
        combined_dict = {}
        for filecrypt, servcoms in self.folder_to_file_crypt_servercoms_dict:
            server_file_list = servcoms.get_file_list()
            combined_dict.update(filecrypt.decrypt_server_file_list(server_file_list))
            # ToDO: handle collisions in keys
        globals.SERVER_FILE_DICT = combined_dict

    def create_shared_folder(self, folder_name: pl.Path, key):
        folder_path = folder_name.absolute()
        folder_path.mkdir()
        file_crypt = FileCryptography(key)
        servercoms = ServComs(self.server_location, hash_key_to_userID(key))
        self.folder_to_file_crypt_servercoms_dict[folder_name] = (file_crypt, servercoms)
        return secretsharing.split_secret(key, 1, 1)

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        file_list = [i.relative_to(globals.WORK_DIR) for i in globals.FILE_FOLDER.glob("**/*.*")]
        return file_list

    def sync_files(self):
        sync_dict = self.generate_sync_dict()
        self.close_observers()
        for file_path in sync_dict:
            c_time, s_time = sync_dict.get(file_path)
            file_path = pl.Path.joinpath(globals.WORK_DIR, file_path)
            if c_time < s_time:  # Server has the newest version
                # Send and delete file locally, such that the client can recover it if needed
                if file_path.exists():
                    self.send_file(file_path)
                    file_path.unlink()
                rel_file_path = file_path.relative_to(globals.WORK_DIR)
                self.get_file(rel_file_path)
            elif c_time > s_time:  # Client has the newest version
                self.send_file(file_path)
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
        self.save_shared_key(key)  # TODO: Implement this
        servercoms = ServComs(self.server_location, hash_key_to_userID(key))
        files = servercoms.get_file_list()
        if len(files) == 0:
            print("Empty shared folder. Put something in the folder to share and try again.")
            return
        file_crypt = FileCryptography(key)
        enc_relative_path, nonce, _ = files[0]
        nonce = bytes.fromhex(nonce)
        try:
            dec_file_rel_path = file_crypt.decrypt_relative_file_path(enc_relative_path, nonce)
        except InvalidTag:
            print("Failed somehow!")
            return
        folder_name: pl.Path = list(dec_file_rel_path.parents)[-2]
        self.folder_to_file_crypt_servercoms_dict[folder_name] = (file_crypt, servercoms)
        self.sync_files()

    def replace_password(self, old_pw, new_pw):  # TODO: Save shared_keys under new pw
        self.sync_files()
        new_key = self.kd.replace_pw(old_pw, new_pw)
        self.userID = hash_key_to_userID(new_key)
        self.file_crypt = FileCryptography(new_key)
        self.servercoms = ServComs(self.server_location, self.userID)
        self.folder_to_file_crypt_servercoms_dict['default'] = self.file_crypt, self.servercoms
        self.sync_files()

    def generate_sync_dict(self):
        """Generates a dictionary with key:files value:(client_time, server_time)
        representing the time stamp of a file for client or server. time stamp 0 = this party does not have the file"""
        # Create a dictionary with key = file name, value = timestamp for local files
        local_file_list = self.get_local_file_list()
        c_dict = {}
        for element in local_file_list:
            c_dict[element] = pl.Path.joinpath(globals.WORK_DIR, element).stat().st_mtime

        # Do the same for server files:
        self.update_server_file_list()
        s_dict = {}

        file_info_object: globals.FileInfo
        for file_info_object in globals.SERVER_FILE_DICT.values():
            s_dict[file_info_object.path] = file_info_object.time_stamp

        # Copy the client dict, and add the uniques from the server dict.
        # Value = 0 since this means the client does not have this file, thus setting a timestamp of as old as possible
        full_dict = c_dict.copy()
        for key in s_dict:
            if key not in full_dict:
                full_dict[key] = 0

        # Create the tuple dictionary key = filename, value = (c_time, s_time)
        for key in full_dict:
            val = s_dict.get(key) if key in s_dict else 0
            full_dict[key] = (full_dict.get(key), val)

        return full_dict

    def save_shared_key(self, key):
        pass  # self.file_crypt.encrypt_key()


def replace_key_from_backup(shares, username, new_pw):
    key = secretsharing.recover_secret(shares)
    keyderivation.KeyDerivation(username).replace_pw_from_key(key, new_pw)
