import pathlib as pl
from resources import globals
from security import keyderivation


class global_test_configer:
    """Class for setting up the test environment, ensuring the testing process does not mess with the user"""

    def __init__(self, kd: keyderivation.KeyDerivation):
        """
        Args:
            kd: the KeyDerivation module of the test user
        """
        self.kd = kd
        self.setup_resources()

    def setup_resources(self):
        """Save the current user profile in memory and clears for test user"""
        try:
            self.key_hashes = self.kd.get_hashes_of_keys()
            pl.Path(globals.KEY_HASHES).unlink()
        except FileNotFoundError:  # File might not exist.
            pass
        try:
            self.enc_old_keys = self.kd.get_enc_old_keys()
            pl.Path(globals.ENC_OLD_KEYS).unlink()
        except FileNotFoundError:  # File might not exist.
            pass
        try:
            with open(globals.SHARED_KEYS, "rt") as file:
                self.shared_folder_keys = file.read()
            globals.SHARED_KEYS.unlink()
        except FileNotFoundError:  # File might not exist at all
            pass

    def recover_shared_keys(self):
        """Stores shared keys to disk from memory"""
        with open(globals.SHARED_KEYS, "wt") as file:
            file.write(self.shared_folder_keys)

    def recover_enc_old_keys(self):
        """Stores the encrypted old keys to disk from memory"""
        for ct_nonce_pair in self.enc_old_keys:
            ct = ct_nonce_pair[0]
            nonce = ct_nonce_pair[1]
            self.kd.append_enc_key_ct_to_enc_keys_file(ct, nonce)

    def recover_key_hashes(self):
        """Stores hash of keys to disk from memory"""
        hashes_str = ""
        for key_hash in self.key_hashes:
            hashes_str += key_hash.hex() + "\n"
        with open(globals.KEY_HASHES, 'w') as file:
            file.write(hashes_str)

    def recover_resources(self):
        """Save the current user profile to the disk from memory, clearing the test user"""
        try:
            self.recover_key_hashes()
        except AttributeError:  # If file not found attribute doesn't exist.
            try:
                pl.Path(globals.KEY_HASHES).unlink()
            except FileNotFoundError:
                pass  # Shouldn't exist and doesn't already
        try:
            self.recover_enc_old_keys()
        except AttributeError:  # If file not found attribute doesn't exist.
            try:
                pl.Path(globals.ENC_OLD_KEYS).unlink()
            except FileNotFoundError:
                pass  # Shouldn't exist and doesn't already
        try:
            self.recover_shared_keys()
        except AttributeError:
            if globals.SHARED_KEYS.exists():
                globals.SHARED_KEYS.unlink()

