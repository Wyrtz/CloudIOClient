import time
import unittest
import pathlib as pl
from security import keyderivation, filecryptography
from resources import globals
from security.keyderivation import BadKeyException, IllegalMethodUsageException


class TestKeyDerivation(unittest.TestCase):

    def setUp(self):
        self.kd = keyderivation.KeyDerivation('12345')
        self.pw = '12345'
        try:
            self.key_hashes_to_save = self.kd.get_hashes_of_keys()
            pl.Path(globals.KEY_HASHES).unlink()
        except FileNotFoundError:  # File might not exist.
            pass
        try:
            self.enc_old_keys = self.kd.get_enc_old_keys()
            pl.Path(globals.ENC_OLD_KEYS).unlink()
        except FileNotFoundError:  # File might not exist.
            pass

    def tearDown(self):
        try:
            recover_key_hashes(self.key_hashes_to_save)
        except AttributeError:  # If file not found attribute doesn't exist.
            try:
                pl.Path(globals.KEY_HASHES).unlink()
            except FileNotFoundError:
                pass  # Shouldn't exist and doesn't already
        try:
            self.recover_enc_old_keys(self.enc_old_keys)
        except AttributeError:  # If file not found attribute doesn't exist.
            try:
                pl.Path(globals.ENC_OLD_KEYS).unlink()
            except FileNotFoundError:
                pass  # Shouldn't exist and doesn't already

    def test_can_derive_a_key(self):
        now = time.time()
        self.kd.derive_key(self.pw, verify=False)
        now_ = time.time()
        time_diff = now_ - now
        # print("\nTook", time_diff, "to derive key.\n")  # For tweaking
        self.assertGreater(time_diff, 1, "Takes less than 1 second to derive key.")

    def test_same_pw_derives_same_pw_while_pw_prime_does_not(self):
        key1 = self.kd.derive_key('12345', verify=False)
        key1_ = self.kd.derive_key('12345', verify=False)
        key2 = self.kd.derive_key('asdfgh', verify=False)
        self.assertTrue(key1 == key1_, "Same pw should derive same pw.")
        self.assertTrue(key1 != key2, "Keys should be different when derived from different passwords.")

    def test_can_verify_valid_key(self):
        key1 = self.kd.derive_new_key(self.pw)
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")

    def test_does_not_verify_bad_key(self):
        key1 = self.kd.derive_new_key('1234')
        key2 = self.kd.derive_key('abcd', verify=False)
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")
        self.assertFalse(self.kd.key_verifies(key2), "Key shouldn't validate.")

    def test_bad_keys_dont_derive(self):
        self.kd.derive_new_key('1234')
        self.assertRaises(keyderivation.BadKeyException,
                          self.kd.derive_key, 'abcd',
                          "Expected bad keys to be detected.")

    def test_new_pw_invalidates_old(self):
        key1 = self.kd.derive_new_key('1234')
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")
        key2 = self.kd.derive_new_key('abcd')
        self.assertTrue(self.kd.key_verifies(key2), "Key doesn't validate.")
        self.assertFalse(self.kd.key_verifies(key1), "Key shouldn't validate.")

    def test_can_replace_pw(self):
        pw_1 = '12345'
        pw_2 = 'abcde'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.kd.replace_pw(pw_1, pw_2)
        key2 = self.kd.derive_key(pw_2)
        self.assertTrue(key1 != key2)

    def test_cannot_replace_pw_with_wrong_pw(self):
        pw_1 = '12345'
        pw_2 = 'abcde'
        pw_3 = 'asdfg'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.assertRaises(BadKeyException, self.kd.replace_pw, pw_3, pw_2)

    def test_cannot_select_first_pw_twice(self):
        pw_1 = '12345'
        pw_2 = 'abcde'
        self.kd.select_first_pw(pw_1)
        self.assertRaises(IllegalMethodUsageException,
                          self.kd.select_first_pw, pw_2)

    def test_cannot_select_first_pw_twice_not_even_the_same(self):
        pw_1 = '12345'
        self.kd.select_first_pw(pw_1)
        self.assertRaises(IllegalMethodUsageException,
                          self.kd.select_first_pw, pw_1)

    def test_can_recover_key_replaced_once(self):
        pw_1 = '12345'
        pw_2 = 'abcde'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.kd.replace_pw(pw_1, pw_2)
        key2 = self.kd.derive_key(pw_2)
        keys = self.kd.retrieve_keys(key2)
        self.assertTrue(len(keys) == 2)
        self.assertTrue(keys[0] == key2, "The first key should be the current key.")
        self.assertTrue(keys[1] == key1, "The second key should be the old key.")

    def recover_enc_old_keys(self, enc_old_keys):
        for ct_nonce_pair in enc_old_keys:
            ct = ct_nonce_pair[0]
            nonce = ct_nonce_pair[1]
            self.kd.append_enc_key_ct_to_enc_keys_file(ct, nonce)

    def recover_key_hashes(self, hashes_of_keys):
        hashes_str = ""
        for key_hash in hashes_of_keys:
            hashes_str += key_hash + "\n"
        with open(globals.KEY_HASHES, 'w') as file:
            file.write(hashes_str)
