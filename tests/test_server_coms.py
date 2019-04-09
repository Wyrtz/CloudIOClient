import unittest

from ServerComs import ServComs
from security import keyderivation
from security.filecryptography import FileCryptography
from resources import globals
import pathlib as pl


class TestServercoms(unittest.TestCase):

    def setUp(self):
        self.serverIp = 'wyrnas.myqnapcloud.com:8000'  # '127.0.0.1:443'
        self.serverComs = ServComs(self.serverIp)
        self.file_name = "pic1.jpg"
        self.file_path = pl.PurePath.joinpath(pl.Path(globals.TEST_FILE_FOLDER), self.file_name)
        self.relative_file_path = self.file_path.relative_to(globals.WORK_DIR)
        self.enc = FileCryptography(keyderivation.KeyDerivation("abc").derive_key("123"))
        self.nonce1 = globals.get_nonce()
        self.nonce2 = globals.get_nonce()

    def test_send_file(self):
        self.send_file(self.nonce1, self.nonce2)

    def test_uploaded_file_in_file_list(self):
        # Send file
        enc_file_path, additional_data = self.send_file(self.nonce1, self.nonce2)
        enc_file_name = enc_file_path.name
        # Get list back from server, and see if it is there
        file_list = self.serverComs.get_file_list()
        self.assertIn(enc_file_name, file_list, "File not on the server!")

    def test_receive_send_file(self):
        with open(self.file_path, 'rb') as file:
            file_content = file.read()
        nonce1 = globals.get_nonce()
        nonce2 = globals.get_nonce()
        enc_file_name = self.enc.encrypt_relative_file_path(self.relative_file_path, nonce1)
        _, additional_data_local = self.send_file(nonce1, nonce2)
        tmp_file_location, additional_data_received = self.serverComs.get_file(enc_file_name)
        self.assertTrue(additional_data_local == additional_data_received, "Additional data has changed during upload.")
        dec_file_path = self.enc.decrypt_file(tmp_file_location, additional_data_received)
        with open(dec_file_path, 'rb') as file:
            received_content = file.read()
        self.assertEqual(file_content, received_content, "Files differ!")

    def send_file(self, nonce1, nonce2):
        enc_file_path, additional_data = self.enc.encrypt_file(self.file_path, nonce1, nonce2)
        self.serverComs.send_file(enc_file_path, additional_data)
        return enc_file_path, additional_data

    def tearDown(self):
        self.serverComs.register_deletion_of_file(self.enc.encrypt_relative_file_path(self.relative_file_path, self.nonce1))
        globals.clear_tmp()
