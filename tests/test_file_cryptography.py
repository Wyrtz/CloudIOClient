import os
import pathlib as pl

import cryptography
import unittest

from filecryptography import FileCryptography
import globals


class test_file_cryptography(unittest.TestCase):
    def setUp(self):
        self.file_name = "client.txt"
        self.file_crypt = FileCryptography()
        self.file_path = pl.PurePath.joinpath(globals.TEST_FILE_FOLDER, self.file_name)

    def test_encrypt_decrypt(self):
        start_file = ""
        end_file = ""
        with open(self.file_path, "rt") as file:
            start_file = file.read()
        file_encrypted, additional_data = self.file_crypt.encrypt_file(self.file_path)
        file_decrypted = self.file_crypt.decrypt_file(file_path=file_encrypted, additional_data=additional_data)
        with open(file_decrypted, "rt") as file:
           end_file = file.read()
        self.assertEqual(start_file, end_file, "Files differ!")

    def test_invalid_tag(self):
        file_encrypted, additional_data = self.file_crypt.encrypt_file(self.file_path)
        with open(file_encrypted, "ab") as file:
            file.write(b'hejjj')
        self.assertRaises(cryptography.exceptions.InvalidTag,
                          self.file_crypt.decrypt_file,
                          file_encrypted, additional_data)

    def test_key_and_salt_saved(self):
        og_salt = self.file_crypt.salt
        og_key = self.file_crypt.key
        file_crypt = FileCryptography()
        new_salt = file_crypt.salt
        new_key = file_crypt.key
        self.assertEqual(og_salt, new_salt, "Salt changed!")
        self.assertEqual(og_key, new_key, "key changed!")

    def tearDown(self) -> None:
        globals.clear_tmp()