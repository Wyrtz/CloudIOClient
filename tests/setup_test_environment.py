import pathlib as pl
from resources import globals


class global_test_configer:

    def __init__(self, kd):
        self.kd = kd
        self.setup_resources()

    def setup_resources(self):
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

    def recover_enc_old_keys(self):
        for ct_nonce_pair in self.enc_old_keys:
            ct = ct_nonce_pair[0]
            nonce = ct_nonce_pair[1]
            self.kd.append_enc_key_ct_to_enc_keys_file(ct, nonce)

    def recover_key_hashes(self):
        hashes_str = ""
        for key_hash in self.key_hashes:
            hashes_str += key_hash + "\n"
        with open(globals.KEY_HASHES, 'w') as file:
            file.write(hashes_str)

    def recover_resources(self):
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
