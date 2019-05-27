import json
import pathlib as pl
from hashlib import sha3_224
from time import sleep

from cryptography.exceptions import InvalidTag
from watchdog.observers import Observer

from ServerComs import ServComs
from file_event_handler import MyHandler
from resources import globals
from resources.globals import FileInfo
from security import keyderivation, secretsharing
from security.filecryptography import FileCryptography


def hash_key_to_userID(key: bytes) -> str:
    """
    method for hashing a key (bytes)
    Args:
        key: the key to be hashed

    Returns:
        str: the hashed and hexed key
    """
    hasher = sha3_224()
    hasher.update(bytes("Keyhash", 'utf-8'))
    hasher.update(key)
    return hasher.digest().hex()


class Client:
    """class for combining different modules into client solution"""

    def __init__(self, username: str, password: str, server_location: str = globals.SERVER_LOCATION,
                 file_folder: pl.Path = globals.FILE_FOLDER) -> None:
        """
        Args:
            username: the username to initialise this clients key
            password:  the password for initialising this clients key
            server_location: the location of the server to host the encrypted files
            file_folder: the main/first folder to watch for file changes
        """
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
        self.folder_to_file_crypt_servercoms_dict.update(self.load_shared_keys())
        self.update_server_file_list()
        self.observers_list = []
        self.start_observing()

    def start_observing(self):
        """Start a folder observer on the main/initial folder"""
        self.start_new_folder_observer(self.file_folder)

    def start_new_folder_observer(self, file_folder_path: pl.Path) -> None:
        """
        Start a new folder observer observing the given path
        Args:
            file_folder_path: the path for observer to start observing for file events
        """
        new_observer = Observer()
        handler = MyHandler(self)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def send_file(self, file_path: pl.Path, file_name_nonce: bytes = globals.generate_random_nonce()) -> None:
        """
        Send the file at the given location encrypted under the given nonce

        Args:
            file_path: the path of the file to send
            file_name_nonce: if provided, the nonce to use when encrypting the file before sending, to ensure getting
                the same filename (used for version control). Otherwise a new nonce

        """
        file_crypt, servercoms = self.get_file_crypt_servercoms(file_path)
        # Encrypt and send the encrypted file
        try:
            file_data_nonce = globals.generate_random_nonce()  # Unique
            enc_file_path, additional_data = file_crypt.encrypt_file(
                file_path, file_name_nonce, file_data_nonce
            )
            servercoms.send_file(enc_file_path, additional_data)
        except PermissionError:
            print("Unable to send file immediately...")
            sleep(1)
            self.send_file(file_path)
            return
        pl.Path.unlink(enc_file_path)  # Delete the encrypted file
        relative_path = file_path.relative_to(globals.WORK_DIR)
        relative_enc_path = enc_file_path.relative_to(globals.TEMPORARY_FOLDER)
        print("File\"" + file_path.stem + "\"send successfully!")
        # Update our local version of the server files
        fio = globals.FileInfo(relative_path, file_name_nonce, relative_enc_path.as_posix(), file_path.stat().st_mtime)
        globals.SERVER_FILE_DICT[fio.path] = fio

    def get_file(self, file_name: str):
        """Encrypt the file name, and request this encrypted file from server.

        Args:
            file_name: the un-encrypted name of the file to request from the server

        """
        file_crypt, servercoms = self.get_file_crypt_servercoms(file_name)
        fio: FileInfo = globals.SERVER_FILE_DICT.get(file_name, None)
        if not fio:
            print("File not found on server")
            return
        try:
            tmp_enc_file_path, additional_data = servercoms.get_file(fio.enc_path)
        except FileNotFoundError:
            print("File not found on server.")
            return
        self.close_observers()
        # globals.DOWNLOADED_FILE_QUEUE.append(file_name) # ToDo: Redundant ?
        file_crypt.decrypt_file(tmp_enc_file_path, additional_data=additional_data)
        pl.Path.unlink(tmp_enc_file_path)
        self.start_observing()

    def delete_remote_file(self, file_rel_path: pl.Path):
        """
        Delete provided file on server by finding its encrypted file name by the provided plain-text file name

        Args:
            file_rel_path: the relative path of the file to be deleted on server

        """
        fio: FileInfo = globals.SERVER_FILE_DICT.get(file_rel_path, None)
        if not fio:
            print("File/dir not on server")
            return
        globals.SERVER_FILE_DICT.pop(file_rel_path)
        _, coms = self.get_file_crypt_servercoms(file_rel_path)
        coms.register_deletion_of_file(fio.enc_path)
        print("File deleted: " + str(fio.path))

    def get_file_crypt_servercoms(self, file_path: pl.Path) -> (FileCryptography, ServComs):
        """
        Look up what servercoms and filecrypt to use for the provided file path

        Args:
            file_path: the path for the file to find the correct assosiated filecrypt and servercoms

        Returns:
            FileCryptography: a filecrypt instance with the correct key for decrypting/encrypting this file
            ServComs: a servercoms instance with the correct userID for this file

        """
        if file_path.is_absolute():
            rel_path = file_path.relative_to(globals.WORK_DIR)
        else:
            rel_path = file_path
        folder_name = pl.Path(rel_path.parts[0]) / rel_path.parts[1]
        file_crypt, servercoms = self.folder_to_file_crypt_servercoms_dict.get(
            folder_name.as_posix(),
            self.folder_to_file_crypt_servercoms_dict.get("default")
        )
        return (file_crypt, servercoms)

    def update_server_file_list(self):
        """Get the filelist from server, decrypt and set globals server file list"""
        combined_dict = {}
        for filecrypt, servcoms in self.folder_to_file_crypt_servercoms_dict.values():
            server_file_list = servcoms.get_file_list()
            combined_dict.update(filecrypt.decrypt_server_file_list(server_file_list))
        globals.SERVER_FILE_DICT = combined_dict

    def create_shared_folder(self, folder_name: pl.Path, key: bytes):
        """
        Create a new folder to be shared and save its assosiated filecrypt and servercoms for later use

        Args:
            folder_name: the name of the folder to be created
            key: the key used for encrypting this folder. Used to create a servercoms and a filecrypt instance for
            this folder
        """
        folder_path = globals.FILE_FOLDER.joinpath(folder_name)
        folder_path.mkdir()
        rel_folder_path = folder_path.relative_to(globals.WORK_DIR)
        # create a filecrypt and servercoms with the provided key
        file_crypt = FileCryptography(key)
        servercoms = ServComs(self.server_location, hash_key_to_userID(key))
        folder_name = pl.Path(rel_folder_path.parts[0]) / rel_folder_path.parts[1]
        # save the created key, filecrypt and servercoms
        self.save_shared_key(folder_name, key)
        self.folder_to_file_crypt_servercoms_dict[folder_name.as_posix()] = (file_crypt, servercoms)

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        file_list = [i.relative_to(globals.WORK_DIR) for i in globals.FILE_FOLDER.glob("**/*.*")]
        return file_list

    def sync_files(self):
        """Sync files between server and client based on what file is the most recent"""
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
        """Close all observers observing a folder, thus ignoring all file events"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()
        return

    def backup_key(self, password: str, required_share_amount_to_recover: int, share_amount: int) -> list:
        """
        Split a password into Shamir Secret Sharing Scheme shares for later recovery

        Args:
            password: The password to back up (the secret)
            required_share_amount_to_recover: How many of the share_amount is needed to recover the password(secret)
            share_amount: How many shares to split the password (secret) into

        Returns:
            list: a list of lists, where each sublist is a (x,y) coordinate along with the shares needed to recover # ToDO: correct ?
        """
        key = self.kd.derive_key(password)
        try:
            return secretsharing.split_secret(key, required_share_amount_to_recover - 1, share_amount)
        except AssertionError:
            print("Invalid amount of shares required to recover from:")
            print("This Secret Sharing scheme implementation supports at max 127 shares to recover from.")
            return []

    def add_share_key(self, key: bytes):
        """
        Add a share_key and thus a shared folder to this account

        Args:
            key: the key for the folder to be shared with this user

        """
        servercoms = ServComs(self.server_location, hash_key_to_userID(key))
        files = servercoms.get_file_list()
        if len(files) == 0:
            print("Empty shared folder. Put something in the folder to share and try again.")
            return
        file_crypt = FileCryptography(key)
        # Get the first file from the list and extract data
        enc_relative_path, nonce, _ = files[0]
        nonce = bytes.fromhex(nonce)
        try:
            dec_file_rel_path = file_crypt.decrypt_relative_file_path(enc_relative_path, nonce)
        except InvalidTag:
            print("Failed somehow!")
            return
        # Use the information of the first file to find the name of the shared folder
        folder_name = pl.Path(dec_file_rel_path.parts[0]) / dec_file_rel_path.parts[1]  # TODO: Bad folder name!!!
        self.save_shared_key(folder_name, key)
        # Save the key and sync
        self.folder_to_file_crypt_servercoms_dict[folder_name.as_posix()] = (file_crypt, servercoms)
        self.sync_files()

    def replace_password(self, old_pw: str, new_pw: str):  # TODO: Save shared_keys under new pw
        """
        change password
        Args:
            old_pw: the password to change from
            new_pw: the password to change to
        """
        # Sync to ensure all files are encrypted on the server under the old password
        self.sync_files()
        new_key = self.kd.replace_pw(old_pw, new_pw)
        self.userID = hash_key_to_userID(new_key)
        self.file_crypt = FileCryptography(new_key)
        self.servercoms = ServComs(self.server_location, self.userID)
        self.folder_to_file_crypt_servercoms_dict['default'] = self.file_crypt, self.servercoms
        # Sync to ensure all files are encrypted on the server under the new password
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

    def save_shared_key(self, folder_path: pl.Path, key: bytes):
        """
        Save the provided shared key to disk

        Args:
            folder_path: the path of the shared folder to save
            key: the key the shared folder is encrypted under
        """
        nonce = globals.generate_random_nonce()
        enc_key = self.file_crypt.encrypt_key(key, nonce)
        new_entry = (folder_path.as_posix(), enc_key.hex(), nonce.hex())
        if globals.SHARED_KEYS.exists():
            data: list = json.loads(open(globals.SHARED_KEYS, "rt").read())
            shared_keys = data.append(new_entry)
        else:
            shared_keys = [new_entry]
        with open(globals.SHARED_KEYS, "wt") as file:
            file.write(json.dumps(shared_keys))

    def load_shared_keys(self) -> dict:
        """
        Load all shared keys from disk and reconstruct the associated servercoms and file_crypt

        Returns:
            dict: a dictionary of servercoms and file crypt, same format as folder_to_file_crypt_servercoms_dict
        """
        dict = {}
        if globals.SHARED_KEYS.exists():
            with open(globals.SHARED_KEYS, "rt") as file:
                data: list = json.loads(file.read())
            for folder_path, enc_key, nonce in data:
                key_bytes = bytes.fromhex(enc_key)
                nonce_bytes = bytes.fromhex(nonce)
                dec_key_bytes = self.file_crypt.decrypt_key(key_bytes, nonce_bytes)
                file_crypt = FileCryptography(key=dec_key_bytes)
                servcoms = ServComs(self.server_location, hash_key_to_userID(dec_key_bytes))
                dict[folder_path] = file_crypt, servcoms
        return dict


def replace_key_from_backup(shares: list, username: str, new_pw: str) -> None:  # ToDo: Test this!!
    """
    Replace the default encryption key from Shamir Secret Sharing Scheme shares

    Args:
        shares: the Shamir Secret Sharing Scheme shares
        username: the new username to create the new client under
        new_pw: the new password to create the new client under
    """
    key = secretsharing.recover_secret(shares)
    old_file_crypt = FileCryptography(key=key)
    new_file_crypt = keyderivation.KeyDerivation(username).replace_pw_from_key(key, new_pw)
    # Encrypt all shared folders keys under the new key
    new_shared_keys = []
    if globals.SHARED_KEYS.exists():
        with open(globals.SHARED_KEYS, "rt") as file:
            data: list = json.load(file.read())
        for folder_path, enc_key, nonce in data:
            key = old_file_crypt.decrypt_key(enc_key, nonce)
            new_nonce = globals.generate_random_nonce()
            new_enc_key = new_file_crypt.encrypt_key(key, new_nonce)
            new_entry = (folder_path, new_enc_key.hex(), new_nonce.hex())
            new_shared_keys.append(new_entry)
        with open(globals.SHARED_KEYS, "wt") as file:
            file.write(json.dumps(new_shared_keys))
