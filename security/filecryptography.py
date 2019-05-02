import json
import os
import pathlib as pl
import platform
import secrets
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from resources import globals


class FileCryptography:

    def __init__(self, key):
        self.aesgcm = AESGCM(key=bytes.fromhex(key))

    def encrypt_relative_file_path(self, relative_file_path, nonce):
        return self.aesgcm.encrypt(
            bytes(str(nonce), 'utf-8'),
            bytes(str(relative_file_path), 'utf-8'),
            associated_data=None).hex() + ".cio"

    def encrypt_file(self, file_path, nonce1, nonce2):
        """Encrypt file_path and return path of the encrypted file"""
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        enc_file_name = self.encrypt_relative_file_path(relative_file_path, nonce1)

        curr_time = time.time()
        additional_data = {'t': curr_time, 'n': enc_file_name, 'nonce1': nonce1, 'nonce2': nonce2}
        additional_data_json = json.dumps(additional_data)

        enc_file_path = pl.Path.joinpath(pl.Path(globals.TEMPORARY_FOLDER), enc_file_name)
        with open(file_path, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(
                bytes(nonce2, 'utf-8'),
                file.read(),
                associated_data=bytes(additional_data_json, 'utf-8'))
            try:
                with open(enc_file_path, "wb") as enc_file:
                    enc_file.write(enc_file_data)
            except FileNotFoundError:
                if platform.system() == "Windows" and len(enc_file_path) > 260:
                    print("Please enable NTFS long paths in your system.(Filesystem Registry entry)")
        return enc_file_path, additional_data

    def decrypt_relative_file_path(self, enc_file_name: pl.Path, nonce):
        enc_file_name = bytes.fromhex(str(enc_file_name.stem))
        return self.aesgcm.decrypt(
            bytes(str(nonce), 'utf-8'), enc_file_name, associated_data=None)

    def decrypt_file(self, file_path, additional_data):
        """Decrypt file_name and return name of the decrypted file"""
        if file_path.suffix != ".cio":
            raise TypeError
        enc_file_name = file_path.stem
        byte_file_name = bytes.fromhex(enc_file_name)
        dec_file_name = self.aesgcm.decrypt(
            bytes(additional_data['nonce1'], 'utf-8'),
            byte_file_name,
            associated_data=None).decode('utf-8')
        dec_file_path = pl.PurePath.joinpath(globals.WORK_DIR, dec_file_name)
        additional_data_json = json.dumps(additional_data)
        dec_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'rb') as file:
            dec_file_data = self.aesgcm.decrypt(
                bytes(additional_data['nonce2'], 'utf-8'),
                file.read(),
                associated_data=bytes(additional_data_json, 'utf-8'))
            with open(dec_file_path, "wb+") as dec_file:
                dec_file.write(dec_file_data)
        globals.DOWNLOADED_FILE_QUEUE.append(dec_file_name)
        return dec_file_path

    def decrypt_file_list_extended(self, enc_relative_path_list_with_nonces: list) -> list:
        file_name_nonce_enc_file_name_triple_list = []
        for enc_relative_path, nonce in enc_relative_path_list_with_nonces:
            try:
                dec_file_name = self.decrypt_relative_file_path(pl.Path(enc_relative_path), nonce)
            except InvalidTag:  # File on server encrypted under another key.
                continue
            file_name_nonce_enc_file_name_triple_list.append([pl.Path(str(dec_file_name, 'utf-8')), nonce, enc_relative_path])
        return file_name_nonce_enc_file_name_triple_list

    def decrypt_file_list(self, enc_relative_path_list_with_nonces: list) -> list:
        """Get a list of encrypted file names, decrypt them, make them to paths and return an unencrypted list"""
        return [lst[0] for lst in self.decrypt_file_list_extended(enc_relative_path_list_with_nonces)]

    def encrypt_key(self, key, nonce):
        return self.aesgcm.encrypt(bytes.fromhex(nonce), bytes.fromhex(key), associated_data=None).hex()

    def decrypt_key(self, ct, nonce):
        return self.aesgcm.decrypt(bytes.fromhex(nonce), bytes.fromhex(ct), associated_data=None).hex()

    def safe_secrets(self):  # TODO: Remove unused and depricated func
        file = open(self.key_path, 'wb')
        file.write(self.key)
        file.close()

        file = open(self.salt_path, "wb")
        file.write(self.salt)
        file.close()

    def get_secrets(self):  # TODO: Remove unused and depricated func
        #ToDo: Save in plaintext ?
        key_exists = os.path.isfile(self.key_path)
        salt_exists = os.path.isfile(self.salt_path)
        if key_exists and salt_exists:
            with open(self.key_path, "rb") as file:
                self.key = file.read()
            with open(self.salt_path, 'rb') as file:
                self.salt = file.read()
        else:
            self.key = AESGCM.generate_key(bit_length=256)
            self.salt = bytes(secrets.token_hex(12), 'utf-8')
            self.safe_secrets()