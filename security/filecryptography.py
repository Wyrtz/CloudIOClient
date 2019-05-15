import json
import os
import pathlib as pl
import platform
import secrets
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from resources import globals


class OlderServerFileError(Exception):
    pass


class FileCryptography:

    def __init__(self, key: bytes):
        self.aesgcm = AESGCM(key=key)

    def encrypt_relative_file_path(self, relative_file_path: pl.Path, nonce: bytes) -> str:
        enc_file_name: str = self.aesgcm.encrypt(
            nonce,
            bytes(relative_file_path.as_posix(), 'utf-8'),
            associated_data=None).hex() + ".cio"
        return enc_file_name

    def encrypt_file(self, file_path, name_nonce: bytes, data_nonce: bytes):
        """Encrypt file_path and return path of the encrypted file"""
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        enc_file_name = self.encrypt_relative_file_path(relative_file_path, name_nonce)

        file_mtime = file_path.stat().st_mtime  # Time of last modification of the file
        additional_data = {'t': file_mtime,
                           'n': enc_file_name,
                           'nonce1': name_nonce.hex(),
                           'nonce2': data_nonce.hex()}
        additional_data_json = json.dumps(additional_data)

        enc_file_path = pl.Path.joinpath(pl.Path(globals.TEMPORARY_FOLDER), enc_file_name)
        with open(file_path, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(
                data_nonce,
                file.read(),
                associated_data=bytes(additional_data_json, 'utf-8'))
            try:
                with open(enc_file_path, "wb") as enc_file:
                    enc_file.write(enc_file_data)
            except FileNotFoundError:
                if platform.system() == "Windows" and len(enc_file_path) > 260:
                    print("Please enable NTFS long paths in your system.(Filesystem Registry entry)")
        return enc_file_path, additional_data

    def decrypt_relative_file_path(self, enc_file_path, nonce: bytes) -> pl.Path:
        enc_file_path = pl.Path(enc_file_path).stem
        enc_file_name = bytes.fromhex(enc_file_path)
        decrypted_file_byte_path: bytes = self.aesgcm.decrypt(
            nonce,
            enc_file_name,
            associated_data=None)
        decrypted_file_path = decrypted_file_byte_path.decode(encoding='utf-8')
        return pl.Path(decrypted_file_path)

    def decrypt_file(self, file_path, additional_data):
        """Decrypt file_name and return name of the decrypted file"""
        if file_path.suffix != ".cio":
            raise TypeError
        enc_file_name = file_path.stem
        byte_file_name = bytes.fromhex(enc_file_name)
        dec_file_name = self.aesgcm.decrypt(
            bytes.fromhex(additional_data['nonce1']),
            byte_file_name,
            associated_data=None).decode('utf-8')
        dec_file_path = pl.Path.joinpath(globals.WORK_DIR, dec_file_name)
        if dec_file_path.exists():
            last_mod_time_c = dec_file_path.stat().st_mtime
            last_mod_time_s = additional_data["t"]
            if last_mod_time_c > last_mod_time_s:
                raise OlderServerFileError("Server send old file to replace local version!")
            # ToDo: Exit gracefully ?
        additional_data_json = json.dumps(additional_data)
        dec_file_path.parent.mkdir(parents=True, exist_ok=True)  # ToDO: Access and Modify data is not true for folders
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
        globals.DOWNLOADED_FILE_QUEUE.append(dec_file_name)
        return dec_file_path

    def decrypt_server_file_list(self, enc_relative_path_list_with_nonces_and_timestamp: list) -> dict:
        file_dict = {}
        for enc_relative_path, nonce, time_stamp in enc_relative_path_list_with_nonces_and_timestamp:
            nonce = bytes.fromhex(nonce)
            time_stamp = float(time_stamp)
            dec_file_rel_path = self.decrypt_relative_file_path(enc_relative_path, nonce)  # Assert Succeeds
            file_dict[dec_file_rel_path] = globals.FileInfo(dec_file_rel_path, nonce, enc_relative_path, time_stamp)
        return file_dict

    def encrypt_key(self, key: bytes, nonce: bytes) -> bytes:
        """Encrypts a key with this file_crypts key"""
        return self.aesgcm.encrypt(nonce, key, associated_data=None)

    def decrypt_key(self, ct: bytes, nonce:bytes) -> bytes:
        """Decrypts an encrypted key with this file_crypts key"""
        return self.aesgcm.decrypt(nonce, ct, associated_data=None)
