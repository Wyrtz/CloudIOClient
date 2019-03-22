import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

class file_cryptography:

    def __init__(self, file_folder, encryption_folder="tmp/"):
        self.folder = file_folder + "/"
        self.get_secrets()
        self.enc_folder = encryption_folder
        self.aesgcm = AESGCM(key=self.key)

    def encrypt_file(self, file_name):
        """Encrypt file_name and return name of the encrypted file"""
        #ToDo: what is "assosiacted data ?
        enc_file_name = self.aesgcm.encrypt(self.salt, file_name.encode('utf-8'), associated_data=None)
        enc_file_name = self.enc_folder + enc_file_name.hex() + ".cio"
        with open(self.folder + file_name, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(self.salt, file.read(), associated_data=None)
            with open(enc_file_name, "wb+") as enc_file:
                enc_file.write(enc_file_data)
        return enc_file_name

    def decrypt_file(self, file_name):
        """Decrypt file_name and return name of the decrypted file"""
        #ToDo: Placing file in files will result in watchdog re-uploading it...
        fragmented_file_name = file_name.split(".")
        if fragmented_file_name[1].lower() != "cio":
            raise TypeError
        byte_file_name = bytes.fromhex(fragmented_file_name[0])
        dec_file_name = self.aesgcm.decrypt(self.salt, byte_file_name, associated_data=None).decode('utf-8')

        with open(self.enc_folder + file_name, 'rb') as file:
            dec_file_data = self.aesgcm.decrypt(self.salt, file.read(), associated_data=None)
            already_exists = os.path.isfile(self.folder + dec_file_name)
            # if already_exists:        #ToDo: handle same file name
            #     fragments = dec_file_name.split(".")
            #     dec_file_name = fragments[0] + "1." + fragments[1]
            with open(self.enc_folder + dec_file_name, "wb+") as dec_file:
                dec_file.write(dec_file_data)
        return dec_file_name

    def safe_stuff(self):
        file = open('key.key', 'wb')
        file.write(self.key)
        file.close()

        file = open("salt.salt", "wb")
        file.write(self.salt)
        file.close()

    def get_secrets(self):
        #ToDo: Save in plaintext ?
        key_exists = os.path.isfile('key.key')
        salt_exists = os.path.isfile('salt.salt')
        if key_exists and salt_exists:
            with open('key.key', "rb") as file:
                self.key = file.read()
            with open('salt.salt', 'rb') as file:
                self.salt = file.read()
            self.safe_stuff()
        else:
            self.key = AESGCM.generate_key(bit_length=256)
            self.salt = bytes(secrets.token_hex(12), 'utf-8')