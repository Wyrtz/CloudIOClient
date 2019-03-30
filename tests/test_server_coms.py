import unittest
import os

from ServerComs import ServComs
from file_cryptography import file_cryptography
import globals


class TestServercoms(unittest.TestCase):
    def setUp(self):
        self.serverIp = 'wyrnas.myqnapcloud.com:8000'
        self.serverComs = ServComs(self.serverIp)
        self.file_name = "pic1.jpg"
        self.file_path = os.path.join(globals.TEST_FILE_FOLDER, self.file_name)
        self.enc = file_cryptography()

    def test_send_file(self):
        self.send_file()

    def test_receive_send_file(self):
        # Send (encrypted) file
        send_file_size = os.stat(self.file_path).st_size
        enc_file_path = self.send_file()
        # Get it back
        response, _ = self.serverComs.get_file(enc_file_path)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200, "Tried to recieve file " + self.file_name)
        dec_file_path = self.enc.decrypt_file(enc_file_path)
        # Make sure the file we got back has the same conten as the one we send (aproxx)
        recv_file_size = os.stat(dec_file_path).st_size
        self.assertEqual(send_file_size, recv_file_size, "Files differs in size!")


    def test_get_file_list(self):
        #Send file
        enc_file_path = self.send_file()
        enc_file_name = enc_file_path.split("\\")[-1]
        #Get list back from server, and see if it is there
        response = self.serverComs.get_file_list()
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)
        jsonRe = response.json()
        file_list = jsonRe["file_list"]
        self.assertIn(enc_file_name, file_list, "File not on the server!")

    def send_file(self):
        enc_file_path = self.enc.encrypt_file(self.file_path)
        response = self.serverComs.send_file(enc_file_path)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200, "Tried to send file " + self.file_name)
        return enc_file_path

    def tearDown(self):
        globals.clear_tmp()
