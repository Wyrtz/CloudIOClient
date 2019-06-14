import json
import os
import pathlib as pl
import platform
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import sha3_512

from resources import globals


class OlderServerFileError(Exception):
    pass


class FileCryptography:
    """Class for encrypting files, keys or strings from the provided key"""

    def __init__(self, key: bytes):
        """
        Args:
            key: the key for all en(de)cryption
        """
        self.aesgcm = AESGCM(key=key)
        hasher = sha3_512()
        hasher.update(key)
        self.hash = hasher.digest().hex()

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        other: FileCryptography = other
        return other.hash == self.hash

    def encrypt_relative_file_path(self, relative_file_path: pl.Path, nonce: bytes) -> str:
        """
        Method for encrypting paths to string on hex format

        Args:
            relative_file_path:  the path to be encrypted
            nonce: the nonce to encrypt the path under along with self.key

        Returns:
            str: the encrypted path as a hexed string

        """
        enc_file_name: str = self.aesgcm.encrypt(
            nonce,
            bytes(relative_file_path.as_posix(), 'utf-8'),
            associated_data=None).hex() + ".cio"
        return enc_file_name

    def encrypt_file(self, file_path: pl.Path, name_nonce: bytes, data_nonce: bytes) -> (pl.Path, dict):
        """Encrypt file_path and return path of the encrypted file

        Args:
            file_path: the path to the file to be encrypted
            name_nonce: the nonce to encrypt the file name under along with self.key
            data_nonce: the nonce to encrypt the file data under along with self.key

        Returns:
            pl.Path: the path of the encrypted file
            dict: a dict with information about said file
        """
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        enc_file_name = self.encrypt_relative_file_path(relative_file_path, name_nonce)

        file_mtime = file_path.stat().st_mtime  # Time of last modification of the file
        additional_data = {'t': file_mtime,
                           'n': enc_file_name,
                           'nonce1': name_nonce.hex(),
                           'nonce2': data_nonce.hex()}
        additional_data_json = json.dumps(additional_data)

        enc_file_path = pl.Path.joinpath(pl.Path(globals.TEMPORARY_FOLDER), enc_file_name)
        # Open the file to be encrypted and extract its data
        with open(file_path, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(
                data_nonce,
                file.read(),
                associated_data=bytes(additional_data_json, 'utf-8'))
            try:
                # create the enctpyted file
                with open(enc_file_path, "wb") as enc_file:
                    enc_file.write(enc_file_data)
            except FileNotFoundError:
                if platform.system() == "Windows" and len(enc_file_path) > 260:
                    print("Please enable NTFS long paths in your system.(Filesystem Registry entry)")
        return enc_file_path, additional_data

    def decrypt_relative_file_path(self, enc_file_path, nonce: bytes) -> pl.Path:
        """
        Decrypt a relative file path into a pl.Path
        Args:
            enc_file_path (str, pl.Path ?): the string to be decrypted
            nonce:  the nonce to decrypt under using self.key

        Returns:
            the decrypted pl.Path

        """
        enc_file_path = pl.Path(enc_file_path)
        if enc_file_path.suffix != ".cio":
            raise TypeError
        enc_file_path = pl.Path(enc_file_path).stem
        enc_file_name = bytes.fromhex(enc_file_path)
        decrypted_file_byte_path: bytes = self.aesgcm.decrypt(
            nonce,
            enc_file_name,
            associated_data=None)
        decrypted_file_path = decrypted_file_byte_path.decode(encoding='utf-8')
        if ".." in decrypted_file_path.split("/"):
            raise PermissionError("Not allowed to ascend folder structure! Don't trust the sender of this file D:")
        return pl.Path(decrypted_file_path)

    def decrypt_file(self, file_path: pl.Path, additional_data: dict) -> pl.Path:
        """Decrypt and create file, retun path of decrypted file

        Args:
            file_path (pl.Path) : the path of the encrypted file to be decrypted
            additional_data (dict) : the additional data needed for decryption, such as nonce

        Returns:
            pl.Path: the path leading to the location of the decrypted file

        """
        dec_file_name = self.decrypt_relative_file_path(file_path, bytes.fromhex(additional_data['nonce1']))
        dec_file_path = pl.Path.joinpath(globals.WORK_DIR, dec_file_name)
        # Check if we already have the file, and if so, if it is newer than our own version
        if dec_file_path.exists():
            last_mod_time_c = dec_file_path.stat().st_mtime
            last_mod_time_s = additional_data["t"]
            if last_mod_time_c > last_mod_time_s:
                raise OlderServerFileError("Server send old file to replace local version!")
            # ToDo: Exit gracefully ?
        additional_data_json = json.dumps(additional_data)
        dec_file_path.parent.mkdir(parents=True, exist_ok=True)  # ToDO: Access and Modify data is not true for folders
        # Open the encrypted file, decrypt it and safe its content to a new file
        with open(file_path, 'rb') as file:
            dec_file_data = self.aesgcm.decrypt(
                bytes.fromhex(additional_data['nonce2']),
                file.read(),
                associated_data=bytes(additional_data_json, 'utf-8'))
            with open(dec_file_path, "wb+") as dec_file:
                dec_file.write(dec_file_data)
        #  Set access and modify as per additional data:
        file_last_mod = additional_data["t"]
        os.utime(str(dec_file_path), (file_last_mod, file_last_mod))
        return dec_file_path

    def decrypt_server_file_list(self, enc_relative_path_list_with_nonces_and_timestamp: list) -> dict:
        """
        Translate a list of encrypted file names into the file names in plain text
        Args:
            enc_relative_path_list_with_nonces_and_timestamp: a list containing lists of these 3 elements

        Returns:
            dict: a dictionary where each sub-list has been made into a FileInfo object with path as key

        """
        file_dict = {}
        for enc_relative_path, nonce, time_stamp in enc_relative_path_list_with_nonces_and_timestamp:
            nonce = bytes.fromhex(nonce)
            time_stamp = float(time_stamp)
            dec_file_rel_path = self.decrypt_relative_file_path(enc_relative_path, nonce)  # Assert Succeeds
            file_dict[dec_file_rel_path] = globals.FileInfo(dec_file_rel_path, nonce, enc_relative_path, time_stamp)
        return file_dict

    def encrypt_key(self, key: bytes, nonce: bytes) -> bytes:
        """Encrypts a key with this file_crypts key

        Args:
            key: the key to be encrypted under self.key. Since key is just bytes, anything could be encrypted under
            self.key using this method, as long as it is on bytes format.
            nonce: the nonce to use with self.key to encrypt the (argument) key

        Returns:
            bytes: the byte representation of the encrypted key
        """
        return self.aesgcm.encrypt(nonce, key, associated_data=None)

    def decrypt_key(self, key_ct: bytes, nonce: bytes) -> bytes:
        """Decrypts an encrypted key with this file_crypts key

        Args:
            key_ct: the key to be decrypted as cipher text. Can decrypt any bytes encrypted using encrypt_key.
            nonce: the nonce to use with self.key to decrypt key_ct

        Returns:
            bytes: the byte representation of the decrypted key
        """
        return self.aesgcm.decrypt(nonce, key_ct, associated_data=None)
