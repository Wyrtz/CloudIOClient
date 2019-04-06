import time
import unittest
import keyderivation
import globals


class TestKeyDerivation(unittest.TestCase):

    def setUp(self):
        self.kd = keyderivation.KeyDerivation('12345')
        self.pw = '12345'
        try:
            self.key_hash_to_save = keyderivation.get_hash_of_key()
        except FileNotFoundError:  # File might not exist.
            pass

    def tearDown(self):
        try:
            recover_key_hash_to_save(self.key_hash_to_save)
        except AttributeError:  # If file not found attribute doesn't exist.
            pass

    def test_can_derive_a_key(self):
        now = time.time()
        self.kd.derive_key(self.pw, verify=False)
        now_ = time.time()
        time_diff = now_ - now
        print("\nTook", time_diff, "to derive key.\n")
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


def recover_key_hash_to_save(hash_of_key):
    with open(globals.KEY_HASH, 'wb') as file:
        file.write(hash_of_key)
