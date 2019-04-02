import unittest
import os

from ServerComs import ServComs
from filecryptography import FileCryptography
import globals


class TestServercoms(unittest.TestCase):

    def setUp(self):
        globals.TESTING = True
        path = os.path.join(os.getcwd(), "..")
        self.serverIp = '127.0.0.1:443'
        self.serverComs = ServComs(self.serverIp)
        self.file_name = "pic1.jpg"
        globals.TEMPORARY_FOLDER = os.path.join(path, "tmp")
        globals.FILE_FOLDER = os.path.join(path, "files_for_testing")
        globals.create_folders()
        self.enc = FileCryptography()

    def test_send_file(self):
        self.send_file()

    def test_uploaded_file_in_file_list(self):
        # Send file
        enc_file_path, additional_data = self.send_file()
        enc_file_name = enc_file_path.split("\\")[-1]
        enc_file_name = enc_file_name.split("/")[-1]
        # Get list back from server, and see if it is there
        file_list = self.serverComs.get_file_list()
        self.assertIn(enc_file_name, file_list, "File not on the server!")

    def test_receive_send_file(self):
        with open(os.path.join(globals.FILE_FOLDER, self.file_name), 'rb') as file:
            file_content = file.read()
        enc_file_name = self.enc.encrypt_filename(self.file_name)
        _, additional_data_local = self.send_file()
        tmp_file_location, additional_data_received = self.serverComs.get_file(enc_file_name)
        self.assertTrue(additional_data_local == additional_data_received, "Additional data has changed during upload.")
        dec_file_path = self.enc.decrypt_file(tmp_file_location, additional_data_received)
        with open(dec_file_path, 'rb') as file:
            received_content = file.read()
        self.assertEqual(file_content, received_content, "Files differ!")

    def send_file(self):
        enc_file_path, additional_data = self.enc.encrypt_file(self.file_name)
        self.serverComs.send_file(enc_file_path, additional_data)
        return enc_file_path, additional_data

    def tearDown(self):
        globals.clear_tmp()
