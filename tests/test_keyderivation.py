import time
import unittest

from security import keyderivation
from security.keyderivation import BadKeyException, IllegalMethodUsageException
from tests import setup_test_environment as ste


class TestKeyDerivation(unittest.TestCase):

    def setUp(self):
        self.username = "abecat"
        self.pw = '12345678901112'
        self.kd = keyderivation.KeyDerivation(self.username)
        self.ste = ste.global_test_configer(self.kd)

    def tearDown(self):
        self.ste.recover_resources()

    def test_can_derive_a_key(self):
        now = time.time()
        self.kd.derive_key(self.pw, verify=False)
        now_ = time.time()
        time_diff = now_ - now
        # print("\nTook", time_diff, "to derive key.\n")  # For tweaking
        self.assertGreater(time_diff, 1, "Takes less than 1 second to derive key.")

    def test_same_pw_derives_same_pw_while_pw_prime_does_not(self):
        key1 = self.kd.derive_key('1234512qweds', verify=False)
        key1_ = self.kd.derive_key('1234512qweds', verify=False)
        key2 = self.kd.derive_key('sed5rfygudews', verify=False)
        self.assertTrue(key1 == key1_, "Same pw should derive same pw.")
        self.assertTrue(key1 != key2, "Keys should be different when derived from different passwords.")

    def test_can_verify_valid_key(self):
        key1 = self.kd.derive_new_key(self.pw)
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")

    def test_does_not_verify_bad_key(self):
        key1 = self.kd.derive_new_key('1234123ewfd23')
        key2 = self.kd.derive_key('abcd12qewdsgte', verify=False)
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")
        self.assertFalse(self.kd.key_verifies(key2), "Key shouldn't validate.")

    def test_bad_keys_dont_derive(self):
        self.kd.derive_new_key('123412q3werfdgd')
        self.assertRaises(keyderivation.BadKeyException,
                          self.kd.derive_key, 'abcd213ewsfdgftre',
                          "Expected bad keys to be detected.")

    def test_new_pw_invalidates_old(self):
        key1 = self.kd.derive_new_key('1234123wef12ew')
        self.assertTrue(self.kd.key_verifies(key1), "Key doesn't validate.")
        key2 = self.kd.derive_new_key('abcd123ewrfdgfhy')
        self.assertTrue(self.kd.key_verifies(key2), "Key doesn't validate.")
        self.assertFalse(self.kd.key_verifies(key1), "Key shouldn't validate.")

    def test_can_replace_pw(self):
        pw_1 = b'1df234512wedf'
        pw_2 = b'abcde123ewrgf'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.kd.replace_pw(pw_1, pw_2)
        key2 = self.kd.derive_key(pw_2)
        self.assertTrue(key1 != key2)

    def test_cannot_replace_pw_with_wrong_pw(self):
        pw_1 = b'12345jy5htgrwe'
        pw_2 = b'abcdeht4rwgff'
        pw_3 = b'asdfg432refwsd'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.assertRaises(BadKeyException, self.kd.replace_pw, pw_3, pw_2)

    def test_cannot_select_first_pw_twice(self):
        pw_1 = b'12345132werfd'
        pw_2 = b'abcde12q3ewrfdg'
        self.kd.select_first_pw(pw_1)
        self.assertRaises(IllegalMethodUsageException,
                          self.kd.select_first_pw, pw_2)

    def test_cannot_select_first_pw_twice_not_even_the_same(self):
        pw_1 = b'1234512q3ewrfd'
        self.kd.select_first_pw(pw_1)
        self.assertRaises(IllegalMethodUsageException,
                          self.kd.select_first_pw, pw_1)

    def test_can_recover_key_replaced_once(self):
        pw_1 = b'123456789011'
        pw_2 = b'abcdewertyuier'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.kd.replace_pw(pw_1, pw_2)
        key2 = self.kd.derive_key(pw_2)
        keys = self.kd.retrieve_keys(key2)
        self.assertTrue(len(keys) == 2)
        self.assertTrue(keys[0] == key2, "The first key should be the current key.")
        self.assertTrue(keys[1] == key1, "The second key should be the old key.")

    def test_can_recover_key_replaced_thrice(self):
        pw_1 = b'1234545678ihgv'
        pw_2 = b'abcdse5dtrguhe'
        pw_3 = b'123a23werdfbcdrguh'
        pw_4 = b'456defdryfguhi'
        self.kd.select_first_pw(pw_1)
        key1 = self.kd.derive_key(pw_1)
        self.kd.replace_pw(pw_1, pw_2)
        key2 = self.kd.derive_key(pw_2)
        self.kd.replace_pw(pw_2, pw_3)
        key3 = self.kd.derive_key(pw_3)
        self.kd.replace_pw(pw_3, pw_4)
        key4 = self.kd.derive_key(pw_4)
        keys = self.kd.retrieve_keys(key4)
        self.assertTrue(len(keys) == 4)
        self.assertTrue(keys[0] == key4, "The first key should be the current key.")
        self.assertTrue(keys[1] == key3, "The second key should be the old key.")
        self.assertTrue(keys[2] == key2, "The second key should be the old key.")
        self.assertTrue(keys[3] == key1, "The second key should be the old key.")
