import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
from globals import globals

class file_cryptography:

    def __init__(self):
        self.key_path = os.path.join(globals.WORK_DIR, 'key.key')
        self.salt_path = os.path.join(globals.WORK_DIR, 'salt.salt')
        self.get_secrets()
        #self.file_folder = os.path.join(os.curdir, file_folder)
        #self.enc_folder = encryption_folder
        self.aesgcm = AESGCM(key=self.key)

    def encrypt_file(self, file_path):
        """Encrypt file_path and return path of the encrypted file"""
        #ToDo: what is "assosiacted data ?
        enc_file_name = self.aesgcm.encrypt(self.salt, file_path.encode('utf-8'), associated_data=None)
        enc_file_name = os.path.join(globals.TEMPORARY_FOLDER, enc_file_name.hex()) + ".cio"
        with open(file_path, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(self.salt, file.read(), associated_data=None)
            with open(enc_file_name, "wb") as enc_file:
                enc_file.write(enc_file_data)
        return enc_file_name

    def decrypt_file(self, file_path):
        """Decrypt file_name and return name of the decrypted file"""
        #ToDo: Placing file in files will result in watchdog re-uploading it...
        fragmented_file_name = file_path.split(".")
        if fragmented_file_name[1].lower() != "cio":
            raise TypeError
        fragmented_file_name = fragmented_file_name[0].split("\\")
        byte_file_name = bytes.fromhex(fragmented_file_name[-1])
        dec_file_name = self.aesgcm.decrypt(self.salt, byte_file_name, associated_data=None).decode('utf-8')
        dec_file_path = os.path.join(globals.FILE_FOLDER, dec_file_name)

        with open(file_path, 'rb') as file:
            dec_file_data = self.aesgcm.decrypt(self.salt, file.read(), associated_data=None)
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