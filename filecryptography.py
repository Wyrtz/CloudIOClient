import json
import os
import platform
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import globals


class FileCryptography:

    def __init__(self):
        self.key_path = os.path.join(globals.curr_path, 'key.key')  # TODO: Temp. Should derive key from pw + salt.
        self.salt_path = os.path.join(globals.curr_path, 'salt.salt')
        self.get_secrets()
        self.aesgcm = AESGCM(key=self.key)

    def encrypt_filename(self, file_name):
        return self.aesgcm.encrypt(self.salt, bytes(file_name, 'utf-8'), associated_data=None).hex() + ".cio"

    def encrypt_file(self, file_name):
        """Encrypt file_path and return path of the encrypted file"""
        enc_file_name = self.encrypt_filename(file_name)
        curr_time = time.time()
        additional_data = {'t': curr_time, 'n': enc_file_name}
        additional_data_json = json.dumps(additional_data)
        print("\nadditional_data_json = ", additional_data_json)
        enc_file_path = os.path.join(globals.TEMPORARY_FOLDER, enc_file_name)
        with open(os.path.join(globals.FILE_FOLDER, file_name), 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(self.salt, file.read(),
                                                associated_data=bytes(additional_data_json, 'utf-8'))
            try:
                with open(enc_file_path, "wb") as enc_file:
                    enc_file.write(enc_file_data)
            except FileNotFoundError:
                if platform.system() == "Windows" and len(enc_file_path) > 260:
                    print("Please enable NTFS long paths in your system.(Filesystem Registry entry)")
        return enc_file_path, additional_data

    def decrypt_file(self, file_path, additional_data):
        """Decrypt file_name and return name of the decrypted file"""
        #ToDo: Placing file in files will result in watchdog re-uploading it...
        fragmented_file_name = file_path.split(".")
        if fragmented_file_name[-1].lower() != "cio":
            raise TypeError
        enc_file_name = fragmented_file_name[-2].split('/')[-1]
        byte_file_name = bytes.fromhex(enc_file_name)
        dec_file_name = self.aesgcm.decrypt(self.salt, byte_file_name, associated_data=None).decode('utf-8')
        dec_file_path = os.path.join(globals.FILE_FOLDER, dec_file_name)
        additional_data_json = json.dumps(additional_data)
        print("\nadditional_data_json = ", additional_data_json)
        with open(file_path, 'rb') as file:  # Doesn't handle bad verification?
            dec_file_data = self.aesgcm.decrypt(self.salt, file.read(), associated_data=bytes(additional_data_json, 'utf-8'))
            with open(dec_file_path, "wb+") as dec_file:
                dec_file.write(dec_file_data)
        globals.DOWNLOADED_FILE_QUEUE.append(dec_file_name)
        return dec_file_path

    def safe_secrets(self):
        file = open(self.key_path, 'wb')
        file.write(self.key)
        file.close()

        file = open(self.salt_path, "wb")
        file.write(self.salt)
        file.close()

    def get_secrets(self):
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