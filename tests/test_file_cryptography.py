import pathlib as pl

import cryptography
import unittest

from security import keyderivation
from security.filecryptography import FileCryptography
import tests.setup_test_environment as ste
from resources import globals
from tests import test_keyderivation


class test_file_cryptography(unittest.TestCase):

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
        with open(self.file_path, "rt") as file:
            start_file = file.read()
        nonce1 = globals.get_nonce()
        nonce2 = globals.get_nonce()
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
        nonce1 = globals.get_nonce()
        nonce2 = globals.get_nonce()
        file_encrypted, additional_data = self.file_crypt.encrypt_file(self.file_path, nonce1, nonce2)
        with open(file_encrypted, "ab") as file:
            file.write(b'hejjj')
        self.assertRaises(cryptography.exceptions.InvalidTag,
                          self.file_crypt.decrypt_file,
                          file_encrypted, additional_data)

    def test_name_encryption(self):
        name_nonce = globals.get_nonce()
        enc_name = self.file_crypt.encrypt_relative_file_path(self.file_path, name_nonce)
        dec_name = self.file_crypt.decrypt_relative_file_path(enc_name, name_nonce)
        self.assertEqual(dec_name, self.file_path)

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
