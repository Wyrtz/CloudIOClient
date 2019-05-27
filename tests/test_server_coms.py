import pathlib as pl
import unittest

import requests

from ServerComs import ServComs
from resources import globals
from security import keyderivation
from tests import setup_test_environment as ste


class TestServercoms(unittest.TestCase):

    def unregister_user(self, userID: str):
        """
        Method for unregistering a user on the server after testing

        Args:
            userID: the user to unregister
        """
        requests.post('https://' + self.serverIp + '/unregister/' + userID, verify=False)

    def setUp(self):
        self.serverIp = 'wyrnas.myqnapcloud.com:8001' # '127.0.0.1:443'
        self.userID = 'aaabbbccc'
        self.serverComs = ServComs(self.serverIp, self.userID)
        self.file_name = "pic1.jpg"
        self.file_path = pl.PurePath.joinpath(pl.Path(globals.TEST_FILE_FOLDER), self.file_name)
        self.relative_file_path = self.file_path.relative_to(globals.WORK_DIR)
        self.kd = keyderivation.KeyDerivation("a3sdfg7h8")
        self.ste = ste.global_test_configer(self.kd)
        self.enc = self.kd.select_first_pw("127834634643")
        self.nonce1 = globals.generate_random_nonce()
        self.nonce2 = globals.generate_random_nonce()

    def test_send_file(self):
        """Test that sending a file does not raise anything and that files are created"""
        enc_file, add_data = self.send_file(self.nonce1, self.nonce2)
        self.assertNotEqual(len(add_data.keys()), 0)


    def test_uploaded_file_in_file_list(self):
        """Test that files are uploaded after creation"""
        # Send file
        enc_file_path, additional_data = self.send_file(self.nonce1, self.nonce2)
        enc_file_name = enc_file_path.name
        # Get list back from server, and see if it is there
        file_list = self.serverComs.get_file_list()
        self.assertIn(enc_file_name, [x[0] for x in file_list], "File not on the server!")

    def test_receive_send_file(self):
        """Test the ability to get a file from the server"""
        with open(self.file_path, 'rb') as file:
            file_content = file.read()
        enc_file_name = self.enc.encrypt_relative_file_path(self.relative_file_path, self.nonce1)
        _, additional_data_local = self.send_file(self.nonce1, self.nonce2)
        tmp_file_location, additional_data_received = self.serverComs.get_file(enc_file_name)
        self.assertTrue(additional_data_local == additional_data_received, "Additional data has changed during upload.")
        dec_file_path = self.enc.decrypt_file(tmp_file_location, additional_data_received)
        with open(dec_file_path, 'rb') as file:
            received_content = file.read()
        self.assertEqual(file_content, received_content, "Files differ!")

    def test_multiple_users_cannot_access_each_others_files(self):
        """test multiple users cannot access other peoples data"""
        userID1 = 'aaaabbbbccccdddd'  # Create three users
        userID2 = 'aaaccccbbbddd'
        userID3 = 'bbbaaadddccccc'
        user1 = ServComs(self.serverIp, userID1)
        user2 = ServComs(self.serverIp, userID2)
        user3 = ServComs(self.serverIp, userID3)
        try:
            nonce1_1 = globals.generate_random_nonce()
            nonce1_2 = globals.generate_random_nonce()
            nonce2_1 = globals.generate_random_nonce()
            nonce2_2 = globals.generate_random_nonce()
            self.send_file(nonce1_1, nonce1_2, user1)  # have two send a file
            self.send_file(nonce2_1, nonce2_2, user2)
            files_user_1 = user1.get_file_list()  # get their files on server back
            files_user_2 = user2.get_file_list()
            files_user_3 = user3.get_file_list()
            self.assertTrue(len(files_user_3) == 0,  # should have right lengths
                            "User 3 has send no files; should have no files.")
            self.assertTrue(len(files_user_1) == 1 and len(files_user_2) == 1,
                            "User 1 & 2 has send 1 file; should have 1 file.")
            for encfilename, nonce, ts in files_user_1:  #
                self.assertTrue([encfilename, nonce] in [[x[0], x[1]] for x in files_user_1])
                self.assertTrue([encfilename, nonce] not in [[x[0], x[1]] for x in files_user_2])
            for encfilename, nonce, ts in files_user_2:
                self.assertTrue([encfilename, nonce] in [[x[0], x[1]] for x in files_user_2])
                self.assertTrue([encfilename, nonce] not in [[x[0], x[1]] for x in files_user_1])
            user1.get_file(files_user_1[0][0])
            user2.get_file(files_user_2[0][0])
            self.assertRaises(FileNotFoundError, user2.get_file, files_user_1[0][0])
            self.assertRaises(FileNotFoundError, user1.get_file, files_user_2[0][0])
        finally:
            self.unregister_user(userID1)
            self.unregister_user(userID2)
            self.unregister_user(userID3)

    def test_equal_method(self):
        """Test comparison of ServerComs (the __eq__ method)"""
        sc1 = ServComs(self.serverIp, "1")
        sc2 = ServComs(self.serverIp, "1")
        sc3 = ServComs(self.serverIp, "2")

        self.assertEqual(sc1, sc2)      # Same ip and id
        self.assertNotEqual(sc1, sc3)   # different ip

    def send_file(self, name_nonce: bytes, data_nonce: bytes, serverComs: ServComs = None) -> (pl.Path, dict):
        """
        Helper method for sending a file

        Args:
            name_nonce: nonce for encrypting the name
            data_nonce: nonce for encrypting the data (content of a file)
            serverComs: the servercoms to use to send the file

        Returns:
            pl.Path: the path of the encrypted file
            dict: a dict containing the additional data
        """
        if not serverComs:
            serverComs = self.serverComs
        enc_file_path, additional_data = self.enc.encrypt_file(self.file_path, name_nonce, data_nonce)
        serverComs.send_file(enc_file_path, additional_data=additional_data)
        return enc_file_path, additional_data

    def tearDown(self):
        self.ste.recover_resources()
        self.serverComs.register_deletion_of_file(
            self.enc.encrypt_relative_file_path(self.relative_file_path, self.nonce1))
        self.unregister_user(self.userID)
        globals.clear_tmp()
