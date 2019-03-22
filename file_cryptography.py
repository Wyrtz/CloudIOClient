import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

class file_cryptography:

    def __init__(self,folder):
        self.folder = folder + "/"
        self.get_secrets()
        self.aesgcm = AESGCM(key=self.key)

    def encrypt_file(self, file_name):
        enc_file_name = file_name + ".cio"
        with open(self.folder + file_name, 'rb') as file:
            enc_file_data = self.aesgcm.encrypt(self.salt, file.read(), associated_data=None)
            with open(self.folder + enc_file_name, "wb+") as enc_file:
                enc_file.write(enc_file_data)
        return enc_file_name

    def decrypt_file(self, file_name):
        dec_file_name = file_name.rsplit(".", 1)[0]
        with open(self.folder + file_name, 'rb') as file:
            dec_file_data = self.aesgcm.decrypt(self.salt,file.read(), associated_data=None)
            already_exists = os.path.isfile(self.folder + dec_file_name)
            # if already_exists:        #ToDo: handle same file name
            #     fragments = dec_file_name.split(".")
            #     dec_file_name = fragments[0] + "1." + fragments[1]
            with open(self.folder + dec_file_name, "wb+") as dec_file:
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