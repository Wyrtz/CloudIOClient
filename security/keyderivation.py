import math
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from hashlib import sha3_512
from threading import Lock
from security import filecryptography
from resources import globals
import pathlib as pl


class KeyDerivation:

    def __init__(self, salt):
        if type(salt) is str:
            salt = bytes(salt, 'utf-8')
        self.salt = salt  # TODO: refactor such that salt is generated randomly and stored with enc of pw to recover old.
        self.kdf = self.new_scrypt
        self.enc_keys_file_lock = Lock()

    def new_scrypt(self):
        return Scrypt(salt=self.salt,  # Should be constant, but randomly chosen. Stored locally.
                      length=32,  # Keylength in bytes. Has to be either 16, 24 or 32 to work with AES-GCM, so 32.
                      n=2 ** (math.floor(32 / 2.5)),  # |Memory_used| = n x r
                      r=32,
                      p=32,  # number of iterations
                      backend=default_backend())

    def derive_key(self, pw, verify=True):  # Assume at first the PW is correct, then check if key is correct.
        key = self.derive_key_unverified(pw)
        if verify and not self.key_verifies(key):
            raise BadKeyException
        return key

    def key_verifies(self, key):  # Check by compare hashing with stored hash of key.
        return get_hashes_of_keys()[-1] == self.hash_key(key)

    def hash_key(self, key):
        hasher = sha3_512()
        hasher.update(bytes("hash key salt", 'utf-8'))  # Its another salt. TODO: random salt?
        hasher.update(bytes.fromhex(key))
        return hasher.digest().hex()

    def derive_new_key(self, pw):
        key = self.derive_key_unverified(pw)
        self.store_hash_of_key(key)
        return key

    def derive_key_unverified(self, pw):
        if type(pw) is str:
            pw = bytes(pw, 'utf-8')
        key = self.kdf().derive(pw)
        return key.hex()

    def store_hash_of_key(self, key):  # Store hash to later compare with another key.
        hash_of_key = self.hash_key(key)  # TODO: hash many iterations?
        # TODO: Add lock on salt (although why would you need it when only 1 instance should ever access it).
        with open(globals.KEY_HASHES, 'a') as file:
            file.write(hash_of_key + "\n")

    def replace_pw(self, old_pw, new_pw):  # It's called future security!
        old_key = self.derive_key(old_pw)
        new_key = self.derive_key(new_pw, False)
        file_crypt = filecryptography.FileCryptography(new_key)
        nonce = globals.get_nonce()
        enc_old_key = file_crypt.encrypt_key(old_key, nonce)
        self.append_enc_key_ct_to_enc_keys_file(enc_old_key, nonce)
        assert self.derive_new_key(new_pw) == new_key  # If wrong something went horribly wrong.
        return file_crypt

    def select_first_pw(self, pw):
        key = self.derive_new_key(pw)
        file_crypt = filecryptography.FileCryptography(key)
        return file_crypt

    def append_enc_key_ct_to_enc_keys_file(self, key_ct, nonce):
        self.enc_keys_file_lock.acquire()
        if not pl.Path(globals.ENC_OLD_KEYS).exists():
            with open(globals.ENC_OLD_KEYS, 'w') as file:
                file.write(key_ct.hex() + " & " + nonce.hex() + "\n")
        else:
            with open(globals.ENC_OLD_KEYS, 'a') as file:
                file.write(key_ct.hex() + " & " + nonce.hex() + "\n")
        self.enc_keys_file_lock.release()


# TODO: Could append hash of key to additional data of file such that we can test fast if file is enc under the ith key.
'''
    def retrieve_old_keys(self, latest_key)
      # Retrieves all old keys by recursively recovering them?
'''


def get_hashes_of_keys():
    with open(globals.KEY_HASHES, 'r') as file:
        hashes_str = file.read()
    return hashes_str.rsplit('\n')[:-1]  # The last item is "".


class BadKeyException(Exception):
    pass
