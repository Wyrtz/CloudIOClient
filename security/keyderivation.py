import math
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from hashlib import sha3_512
from threading import Lock
from security import filecryptography
from resources import globals
import pathlib as pl


class KeyDerivation:
    """Class for deriving keys from strings (passwords)"""

    def __init__(self, username: str):
        """
        Args:
            username: the username to use as salt
        """
        if len(username) < 5:
            raise BadUsernameSelected
        self.salt = bytes(username, 'utf-8')
        self.kdf = self.new_scrypt
        self.enc_keys_file_lock = Lock()
        self.key_hashes_lock = Lock()

    def new_scrypt(self) -> Scrypt:
        """
        Method for creating a new scrypt

        Returns:
            Scrypt initialised with self.salt
        """
        return Scrypt(salt=self.salt,  # Should be constant, but randomly chosen. Stored locally.
                      length=32,  # Keylength in bytes. Has to be either 16, 24 or 32 to work with AES-GCM, so 32.
                      n=2 ** (math.floor(32 / 2.5)),  # |Memory_used| = n x r
                      r=32,
                      p=32,  # number of iterations
                      backend=default_backend())

    def derive_key(self, pw: str, verify: bool=True) -> bytes:  # Assume at first the PW is correct, then check if
        # key is
        """
        Derive a key from a password
        Args:
            pw: a string to create the key from
            verify: whether or not to verify if the provided password is the current users password

        Returns:
            bytes: A key in the form of bytes
        """
        key = self.derive_key_unverified(pw)
        if verify and not self.key_verifies(key):
            raise BadKeyException
        return key

    def key_verifies(self, key):
        """Check by compare hashing with stored hash of key."""
        hashes = self.get_hashes_of_keys()
        if len(hashes) == 0:
            return False
        return hashes[-1] == self.hash_key(key)

    def hash_key(self, key: bytes) -> bytes:
        """
        Hash a key using sha3_512

        Args:
            key: the key to be hashed

        Returns:
            bytes: the hashed key
        """
        hasher = sha3_512()
        hasher.update(bytes("hash key salt", 'utf-8'))  # Its another salt.
        hasher.update(self.salt)
        hasher.update(key)
        return hasher.digest()

    def derive_new_key(self, pw: str) -> bytes:
        """
        Derive a (new) key from the provided password and stores the key hashed

        Args:
            pw: the password to derive a new key from

        Returns:
            bytes: the new key
        """
        key = self.derive_key_unverified(pw)
        self.store_hash_of_key(key)
        return key

    def derive_key_unverified(self, pw: str) -> bytes:
        """
        Derive a key from a password

        Args:
            pw: the password to derive a key from

        Returns:
            bytes: the key
        """
        if type(pw) is str:
            pw = bytes(pw, 'utf-8')
        key = self.kdf().derive(pw)
        return key

    def store_hash_of_key(self, key: bytes) -> None:
        """
        Store hash to later compare with another key's hash.

        Args:
            key: the key to hash and store
        """

        self.key_hashes_lock.acquire()
        hash_of_key = self.hash_key(key)  # TODO: hash many iterations?
        with open(globals.KEY_HASHES, 'a') as file:
            file.write(hash_of_key.hex() + "\n")
        self.key_hashes_lock.release()

    def replace_pw(self, old_pw: str, new_pw: str) -> bytes:  # It's called future security!
        """
        Replace password and update current user, provided the old password is correct and the new is valid.

        Args:
            old_pw: the previous password
            new_pw: the new password

        Returns:
            bytes: the new key
        """
        if not self.has_password():
            raise IllegalMethodUsageException()
        if len(new_pw) < 12:
            raise BadPasswordSelected
        old_key = self.derive_key(old_pw)
        new_key = self.derive_key(new_pw, False)
        file_crypt = filecryptography.FileCryptography(new_key)
        nonce = globals.generate_random_nonce()
        enc_old_key = file_crypt.encrypt_key(old_key, nonce)
        self.append_enc_key_ct_to_enc_keys_file(enc_old_key, nonce)
        self.store_hash_of_key(new_key)
        return new_key

    def select_first_pw(self, pw: str) -> filecryptography.FileCryptography:
        """
        Select first password and update current user

        Args:
            pw: the new password to derive a new key from

        Returns:
            FileCryptography: a filecryptography object, encrypting and decrypting under the new key (derived from
            the pw)

        """
        if len(pw) < 12:
            raise BadPasswordSelected
        if self.has_password():
            raise IllegalMethodUsageException()
        key = self.derive_new_key(pw)
        file_crypt = filecryptography.FileCryptography(key)
        return file_crypt

    def append_enc_key_ct_to_enc_keys_file(self, key_ct: bytes, nonce: bytes):
        """
        Read the name

        Args:
            key_ct: the encrypted key (key ciphertext) to be stored as being the previous newest key
            nonce: the nonce the encrypted key is encrypted under
        """
        self.enc_keys_file_lock.acquire()
        if not pl.Path(globals.ENC_OLD_KEYS).exists():
            with open(globals.ENC_OLD_KEYS, 'w') as file:
                file.write(key_ct.hex() + " & " + nonce.hex() + "\n")
        else:
            with open(globals.ENC_OLD_KEYS, 'a') as file:
                file.write(key_ct.hex() + " & " + nonce.hex() + "\n")
        self.enc_keys_file_lock.release()

    def retrieve_keys(self, current_key: bytes) -> list:
        """
        Get all stored keys used previously

        Args:
            current_key: the latest key. This is what previous current key is encrypted under

        Returns:
            list: the list of retrieved previous keys

        To retrieve old keys we need their
        - hashes to verify,
        - cypher texts
        - nonces
        Since key_0 = dec(dec(...(key_curr, nonce_curr), nonce_curr-1)...), nonce_0)
        we need to work our way from most recent to oldest key.
        While doing this we can verify if key_i is correct as it should hash to the hash_i.
        """
        successor_key = current_key  # The former key is encrypted under its successor and the nonce given.
        old_enc_keys = self.get_enc_old_keys()
        key_hashes_stored = self.get_hashes_of_keys()
        key_hashes_stored.reverse()  # Most recent, last added at bottom, first to decrypt.
        # We now have [[ct_curr-1, nonce_curr-1], ..., [ct_0, nonce_0]] & [hash_curr, hash_curr-1, ..., hash_0]
        keys = [successor_key]  # The list of reconstructed keys.
        if not key_hashes_stored[0] == self.hash_key(successor_key):  # Is hash(key) == hash(key_curr)?
            raise BadKeyException  # If not; bad key.
        for idx, ct_nonce_pair in enumerate(old_enc_keys):
            ct = ct_nonce_pair[0]
            nonce = ct_nonce_pair[1]
            file_crypt = filecryptography.FileCryptography(successor_key)  # ... the previous key.
            successor_key = file_crypt.decrypt_key(ct, nonce)  # With those we decrypt. Successor_key technically predecessor
            hash_of_key = self.hash_key(successor_key)
            if not hash_of_key == key_hashes_stored[idx + 1]:  # We then verify the hash is correct.
                raise BadKeyException  # If not, bad key we decrypted. Assuming hash is correct only pw can be at fault.
            keys.append(successor_key)  # If is good hash, store it and continue to the next.
        return keys

    def get_enc_old_keys(self) -> list:
        """
        Retrive (encrypted) list of all previously used keys,

        Returns:
            list: list of cipher texts of old keys
        """
        self.enc_keys_file_lock.acquire()
        if not pl.Path(globals.ENC_OLD_KEYS).exists():
            self.enc_keys_file_lock.release()
            raise FileNotFoundError
        with open(globals.ENC_OLD_KEYS, 'r') as file:
            old_enc_keys_str = file.read()
        self.enc_keys_file_lock.release()
        old_enc_keys_str_arr = old_enc_keys_str.rsplit('\n')
        old_enc_keys = []
        for s in old_enc_keys_str_arr:
            if s == "":  # There will be an empty entry at the end - Just ignore it.
                continue
            old_enc_keys = [s.rsplit(" & ")] + old_enc_keys  # first in, last out; this is the order we need to dec.
        return [[bytes.fromhex(element[0]), bytes.fromhex(element[1])] for element in old_enc_keys]

    def get_hashes_of_keys(self):
        """Retrieve the hashed keys from disk"""
        self.key_hashes_lock.acquire()
        try:
            with open(globals.KEY_HASHES, 'r') as file:
                hashes_str = file.read()
        except FileNotFoundError:
            self.key_hashes_lock.release()
            return []
        self.key_hashes_lock.release()
        byte_keys = [bytes.fromhex(x) for x in hashes_str.rsplit('\n')]
        return byte_keys[:-1]  # The last item is "".

    def has_password(self):
        """Check whether any password is already set"""
        return len(self.get_hashes_of_keys()) != 0
        # Only way we can know if we have a pw is if we have something to compare it with.

    def replace_pw_from_key(self, key: bytes, new_pw: str) -> filecryptography.FileCryptography:
        """
        Replace password and update current user, provided the key is currenct key and new password is valid

        Args:
            key: the current key to check against the hashed key
            new_pw: the new password

        Returns:
            FileCryptography: the FileCrypt object to encrypt and decrypt under the new key derived from the new
            password

        """
        if len(new_pw) < 12:
            raise BadPasswordSelected
        if not self.key_verifies(key):
            raise BadKeyException
        new_key = self.derive_key(new_pw, False)
        file_crypt = filecryptography.FileCryptography(new_key)
        nonce = globals.generate_random_nonce()
        enc_old_key = file_crypt.encrypt_key(key, nonce)
        self.append_enc_key_ct_to_enc_keys_file(enc_old_key, nonce)
        self.store_hash_of_key(new_key)
        return file_crypt


class BadKeyException(Exception):
    pass


class IllegalMethodUsageException(Exception):
    pass


class BadPasswordSelected(Exception):
    pass


class BadUsernameSelected(Exception):
    pass
