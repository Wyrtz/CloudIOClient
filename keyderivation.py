import math
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from hashlib import sha3_512
import filecryptography
import globals


class KeyDerivation:  # TODO: Refactor project structure; crypt folder with this and filecrypt. Keyhash and salt in resource folder.

    def __init__(self, salt):
        if type(salt) is str:
            salt = bytes(salt, 'utf-8')
        self.salt = salt
        self.kdf = self.new_scrypt

    def new_scrypt(self):
        return Scrypt(salt=self.salt,  # Should be constant, but randomly chosen. Stored locally.
                      length=32,  # Keylength in bytes. Has to be either 16, 24 or 32 to work with AES-GCM, so 32.
                      n=2 ** (math.floor(32 / 2.5)),  # |Memory_used| = n x r
                      r=32,
                      p=32,  # number of iterations
                      backend=default_backend())

    def derive_key(self, pw, verify=True):  # Assume at first the PW is correct, then check if key is correct.
        if type(pw) is str:
            pw = bytes(pw, 'utf-8')
        key = self.kdf().derive(pw)
        if verify and not self.key_verifies(key):
            raise BadKeyException
        return key

    def key_verifies(self, key):  # Check by compare hashing with stored hash of key.
        return get_hash_of_key() == self.hash_key(key)

    def hash_key(self, key):
        hasher = sha3_512()
        hasher.update(bytes("hash key salt", 'utf-8'))  # Its another salt. TODO: random salt?
        hasher.update(key)
        return hasher.digest()

    def derive_new_key(self, pw):
        if type(pw) is str:
            pw = bytes(pw, 'utf-8')
        key = self.kdf().derive(pw)
        self.store_hash_of_key(key)
        return key  # TODO: Maybe return nothing?

    def store_hash_of_key(self, key):  # Store hash to later compare with another key.
        hash_of_key = self.hash_key(  # TODO: hash many iterations?
            key)  # TODO: Add lock on salt (although why would you need it when only 1 instance should ever access it).
        with open(globals.KEY_HASH, 'wb') as file:
            file.write(hash_of_key)

    def replace_pw(self, old_pw, new_pw):  # It's called future security!
        old_key = self.derive_key(old_pw)
        new_key = self.derive_new_key(new_pw)
        # filecryptography.FileCryptography()


def get_hash_of_key():
    with open(globals.KEY_HASH, 'rb') as file:
        return file.read()


class BadKeyException(Exception):
    pass
