import pathlib as pl

import cryptography
import unittest

from security import keyderivation
from security.filecryptography import FileCryptography
import tests.setup_test_environment as ste
from resources import globals
from tests import test_keyderivation


class test_file_cryptography(unittest.TestCase):
    """Class for unittesting the filecryptography.py module"""

    def setUp(self):
        self.file_name = "client.txt"
        self.file_path = pl.PurePath.joinpath(globals.TEST_FILE_FOLDER, self.file_name)
        self.kd = keyderivation.KeyDerivation('12345')
        self.ste = ste.global_test_configer(self.kd)
        self.file_crypt = self.kd.select_first_pw("abecattemadet")

    def tearDown(self):
        self.ste.recover_resources()
        globals.clear_tmp()

    def test_encrypt_decrypt(self):
        """test file can be encrypted and then decrypted"""
        with open(self.file_path, "rt") as file:
            start_file = file.read()
        nonce1 = globals.generate_random_nonce()
        nonce2 = globals.generate_random_nonce()
        encrypted_file_path, additional_data = self.file_crypt.encrypt_file(
            self.file_path,
            nonce1,
            nonce2)
        file_decrypted = self.file_crypt.decrypt_file(
            file_path=encrypted_file_path,
            additional_data=additional_data)
        with open(file_decrypted, "rt") as file:
           end_file = file.read()
        self.assertEqual(start_file, end_file, "Files differ!")

    def test_invalid_tag(self):
        """test that messing with the encrypted file leads to error when decrypting (authentication fail)"""
        nonce1 = globals.generate_random_nonce()
        nonce2 = globals.generate_random_nonce()
        file_encrypted, additional_data = self.file_crypt.encrypt_file(self.file_path, nonce1, nonce2)
        with open(file_encrypted, "ab") as file:
            file.write(b'hejjj')
        self.assertRaises(cryptography.exceptions.InvalidTag,
                          self.file_crypt.decrypt_file,
                          file_encrypted, additional_data)

    def test_name_encryption(self):
        """test the ability to encrypt and decrypt a path"""
        name_nonce = globals.generate_random_nonce()
        enc_name = self.file_crypt.encrypt_relative_file_path(self.file_path, name_nonce)
        self.assertNotEqual(enc_name, self.file_path)  # The name was in fact encrypted
        dec_name = self.file_crypt.decrypt_relative_file_path(enc_name, name_nonce)
        self.assertEqual(dec_name, self.file_path)     # We get the same name back

    def test_filecrypt_compare_method(self):
        """test that comparing filecrypts (the __eq__ method) works as expected"""
        key1 = globals.generate_random_key()
        key2 = globals.generate_random_key()
        fc1 = FileCryptography(key1)
        fc2 = FileCryptography(key1)
        fc3 = FileCryptography(key2)
        self.assertEqual(fc1, fc2)
        self.assertNotEqual(fc1, fc3)

    def test_illegal_file_path_decryption(self):
        """test that illegal paths are not accepted """
        nonce = globals.generate_random_nonce()
        file_path = pl.Path(pl.Path.cwd() / "..")
        enc_file_path = self.file_crypt.encrypt_relative_file_path(file_path, nonce)
        self.assertRaises(PermissionError, self.file_crypt.decrypt_relative_file_path, enc_file_path, nonce)

    def recover_enc_old_keys(self, enc_old_keys):
        """Not used..."""
        for ct_nonce_pair in enc_old_keys:
            ct = ct_nonce_pair[0]
            nonce = ct_nonce_pair[1]
            self.kd.append_enc_key_ct_to_enc_keys_file(ct, nonce)

    def recover_key_hashes(self, hashes_of_keys):
        """Not used..."""
        hashes_str = ""
        for key_hash in hashes_of_keys:
            hashes_str += key_hash + "\n"
        with open(globals.KEY_HASHES, 'w') as file:
            file.write(hashes_str)
