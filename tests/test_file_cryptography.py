import cryptography
import unittest
from time import sleep

from file_cryptography import file_cryptography


class test_file_cryptography(unittest.TestCase):
    def setUp(self):
        self.folder = '../files_for_testing'
        self.file_crypt = file_cryptography(file_folder=self.folder)

    def test_encrypt_decrypt(self):
        file_name = "client.txt"
        start_file = ""
        end_file = ""
        with open(self.folder + "/" + file_name, "rt") as file:
            start_file = file.read()
        file_encrypted = self.file_crypt.encrypt_file(file_name=file_name)
        file_decrypted = self.file_crypt.decrypt_file(file_name=file_encrypted)
        with open(self.folder + "/" + file_decrypted, "rt") as file:
           end_file = file.read()
        self.assertEqual(start_file, end_file, "Files differ!")

    def test_invalid_tag(self):
        file_name = "client.txt"
        file_encrypted = self.file_crypt.encrypt_file(file_name=file_name)
        with open(self.folder + "/" + file_encrypted, "ab") as file:
            file.write(b'hejjj')
        self.assertRaises(cryptography.exceptions.InvalidTag, self.file_crypt.decrypt_file, file_encrypted)


if __name__ == '__main__':
    unittest.main()
