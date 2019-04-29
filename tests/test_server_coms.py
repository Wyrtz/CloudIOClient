import pathlib as pl
import unittest

import requests

from ServerComs import ServComs
from resources import globals
from security import keyderivation
from tests import setup_test_environment as ste


class TestServercoms(unittest.TestCase):

    def register_user(self, userID):
        requests.post('https://' + self.serverIp + '/register/' + userID, verify=False)

    def unregister_user(self, userID):
        requests.post('https://' + self.serverIp + '/unregister/' + userID, verify=False)

    def setUp(self):
        self.serverIp = '127.0.0.1:443' # 'wyrnas.myqnapcloud.com:8000'
        self.serverComs = ServComs(self.serverIp)
        self.file_name = "pic1.jpg"
        self.file_path = pl.PurePath.joinpath(pl.Path(globals.TEST_FILE_FOLDER), self.file_name)
        self.relative_file_path = self.file_path.relative_to(globals.WORK_DIR)
        self.kd = keyderivation.KeyDerivation("a3sdfg7h8")
        self.ste = ste.global_test_configer(self.kd)
        self.enc = self.kd.select_first_pw("127834634643")
        self.nonce1 = globals.get_nonce()
        self.nonce2 = globals.get_nonce()
        self.userID = 'aaabbbccc'
        self.register_user(self.userID)

    def test_send_file(self):
        self.send_file(self.nonce1, self.nonce2, self.userID)

    def test_uploaded_file_in_file_list(self):
        # Send file
        enc_file_path, additional_data = self.send_file(self.nonce1, self.nonce2, self.userID)
        enc_file_name = enc_file_path.name
        # Get list back from server, and see if it is there
        file_list = self.serverComs.get_file_list(self.userID)
        self.assertIn([enc_file_name, self.nonce1], file_list, "File not on the server!")

    def test_receive_send_file(self):
        with open(self.file_path, 'rb') as file:
            file_content = file.read()
        enc_file_name = self.enc.encrypt_relative_file_path(self.relative_file_path, self.nonce1)
        _, additional_data_local = self.send_file(self.nonce1, self.nonce2, self.userID)
        tmp_file_location, additional_data_received = self.serverComs.get_file(enc_file_name, self.userID)
        self.assertTrue(additional_data_local == additional_data_received, "Additional data has changed during upload.")
        dec_file_path = self.enc.decrypt_file(tmp_file_location, additional_data_received)
        with open(dec_file_path, 'rb') as file:
            received_content = file.read()
        self.assertEqual(file_content, received_content, "Files differ!")

    def send_file(self, nonce1, nonce2, userID):
        enc_file_path, additional_data = self.enc.encrypt_file(self.file_path, nonce1, nonce2)
        self.serverComs.send_file(enc_file_path, userID=userID, additional_data=additional_data)
        return enc_file_path, additional_data

    def tearDown(self):
        self.ste.recover_resources()
        self.serverComs.register_deletion_of_file(self.enc.encrypt_relative_file_path(self.relative_file_path, self.nonce1), self.userID)
        self.unregister_user(self.userID)
        globals.clear_tmp()

    def test_multiple_users_cannot_access_each_others_files(self):
        userID1 = 'aaaabbbbccccdddd'  # Create three users
        userID2 = 'aaaccccbbbddd'
        userID3 = 'bbbaaadddccccc'
        self.register_user(userID1)
        self.register_user(userID2)
        self.register_user(userID3)
        try:
            nonce1_1 = globals.get_nonce()
            nonce1_2 = globals.get_nonce()
            nonce2_1 = globals.get_nonce()
            nonce2_2 = globals.get_nonce()
            self.send_file(nonce1_1, nonce1_2, userID1)  # have two send a file
            self.send_file(nonce2_1, nonce2_2, userID2)
            files_user_1 = self.serverComs.get_file_list(userID1)  # get their files on server back
            files_user_2 = self.serverComs.get_file_list(userID2)
            files_user_3 = self.serverComs.get_file_list(userID3)
            self.assertTrue(len(files_user_3) == 0,  # should have right lengths
                            "User 3 has send no files; should have no files.")
            self.assertTrue(len(files_user_1) == 1 and len(files_user_2) == 1,
                            "User 1 & 2 has send 1 file; should have 1 file.")
            for encfilename, nonce in files_user_1:  #
                self.assertTrue([encfilename, nonce] in files_user_1)
                self.assertTrue([encfilename, nonce] not in files_user_2)
            for encfilename, nonce in files_user_1:
                self.assertTrue([encfilename, nonce] in files_user_1)
                self.assertTrue([encfilename, nonce] not in files_user_2)
            self.serverComs.get_file(files_user_1[0][0], userID1)
            self.serverComs.get_file(files_user_2[0][0], userID2)
            self.assertRaises(FileNotFoundError, self.serverComs.get_file, files_user_1[0][0], userID2)
            self.assertRaises(FileNotFoundError, self.serverComs.get_file, files_user_2[0][0], userID1)
        finally:
            self.unregister_user(userID1)
            self.unregister_user(userID2)
            self.unregister_user(userID3)

    # TODO: test_can_retrieve_old_files_under new alias(self):