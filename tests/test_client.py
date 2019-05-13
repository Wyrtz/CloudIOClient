import os
import pathlib as pl
import unittest
from time import sleep

import requests

import client
from client import Client
from resources import globals
from security import keyderivation
from tests import setup_test_environment as ste


class TestClient(unittest.TestCase):

    def unregister_user(self, userID):
        requests.post('https://' + self.serverIp + '/unregister/' + userID, verify=False)

    def setUp(self):
        self.serverIp = 'wyrnas.myqnapcloud.com:8001' #'127.0.0.1:443'
        self.sleep_time = 1
        self.random_files_list = []
        self.username = "abecattematteman"
        self.pw = '1234567890101112'
        self.kd = keyderivation.KeyDerivation(self.username)
        self.ste = ste.global_test_configer(self.kd)
        self.enc = self.kd.select_first_pw(self.pw)
        self.client = Client(username=self.username, password=self.pw, server_location=self.serverIp)

    def tearDown(self):
        self.ste.recover_resources()
        for file in self.random_files_list:
            if pl.Path.exists(file):
                pl.Path.unlink(file)
        globals.clear_tmp()
        self.client.close_observers()
        self.unregister_user(self.client.userID)

    def test_created_file_is_uploaded(self):
        """Create a new random file and place it in files folder for upload"""
        random_file_path = self.create_random_file().relative_to(globals.WORK_DIR)
        sleep(self.sleep_time)
        self.client.update_server_file_list()
        server_files = list(globals.SERVER_FILE_DICT)
        self.assertIn(random_file_path, server_files)

    def test_delete_file(self):
        """Create file, delete it, check if it is deleted on server"""
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        sleep(1)
        pl.Path.unlink(random_file_path)
        self.random_files_list.remove(random_file_path)
        sleep(self.sleep_time)
        self.assertNotIn(random_file_relative_path, self.client.get_local_file_list())
        self.client.update_server_file_list()
        self.assertNotIn(random_file_relative_path, list(globals.SERVER_FILE_DICT))

    def test_retrieve_file_from_server(self):
        """Create new file, make sure it is uploaded, delete it locally, get it back"""
        # Create file, wait, check if it was uploaded
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        random_file_name = pl.Path(random_file_path.name)
        sleep(self.sleep_time)
        self.client.update_server_file_list()
        server_file_paths = list(globals.SERVER_FILE_DICT)
        self.assertIn(random_file_relative_path, server_file_paths)
        # Delete the file locally, "close client" such that the server is not asked to also delete (archive)
        self.client.close_observers()
        sleep(0.2)
        pl.Path.unlink(random_file_path)
        self.assertNotIn(random_file_name, self.client.get_local_file_list())
        # Get file back, make sure we got it
        self.client.get_file(random_file_relative_path)
        sleep(self.sleep_time)
        self.assertIn(random_file_relative_path, self.client.get_local_file_list())

    def test_modify_file(self):
        """Create a file, modify it serveral times, get it back from server and ensure all modifications are present"""
        # Create a file
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        random_file_name = pl.Path(random_file_path.name)
        # Modify the file and save/close
        sleep(0.5)
        with open(random_file_path, "ab") as file:
            file.write(os.urandom(1024))
        # Modify the file and save/close
        sleep(0.5)
        with open(random_file_path, "ab") as file:
            file.write(os.urandom(1024))
        # Modify the file and save/close
        sleep(0.5)
        with open(random_file_path, "ab") as file:
            file.write(os.urandom(1024))
        # Close client
        sleep(0.5)
        self.client.close_observers()
        with open(random_file_path, "rb") as file:
            local_file_data = file.read()
        # Delete file
        pl.Path.unlink(random_file_path)
        # Get it back from server
        self.client.get_file(random_file_relative_path)
        sleep(self.sleep_time)
        # Make sure it contains all modification!
        with open(random_file_path, "rb") as file:
            remote_file_data = file.read()
        self.assertEqual(local_file_data, remote_file_data, "Files not equal!")

    def test_can_backup_key_then_replace(self):
        shares = self.client.backup_key(self.pw, 10, 20)
        self.assertTrue(len(shares) == 20)
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[:9], self.username, 'wertyuisdfgh')
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[5:9], self.username, 'wertyuisdfgh')
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[5:14], self.username, 'wertyuisdfgh')
        new_pw = 'wertyuiosdfghj'
        client.replace_key_from_backup(shares[3:15], self.username, new_pw)
        self.client.kd.derive_key(new_pw)

    # def test_get_file_crypt(self):
    #     # Create 3 file_crypt from 3 keys:
    #     user_1 = "qwerty"
    #     user_2 = "asdfgh"
    #     user_3 = "zxcvbn"
    #     pw_1 = "qwertyuiiopå¨"
    #     pw_2 = "asdfghjklæø*"
    #     pw_3 = "<>zxcvbnm,.-"
    #     kd1 = keyderivation.KeyDerivation(user_1)
    #     key1 = kd1.derive_key(pw_1)
    #     file_crypt_1 = FileCryptography(key1)
    #     kd2 = keyderivation.KeyDerivation(user_2)
    #     key2 = kd1.derive_key(pw_2)
    #     file_crypt_2 = FileCryptography(key2)
    #     kd3 = keyderivation.KeyDerivation(user_3)
    #     key3 = kd1.derive_key(pw_3)
    #     file_crypt_3 = FileCryptography(key3)
    #     defualt_file_crypt= self.client.file_crypt
    #     p1 = pl.Path(cw)
    #     p2
    #     p3
    #     self.client.file_crypt_dict[]


    def create_random_file(self, path=globals.FILE_FOLDER):
        """Create a random file in the file folder, give back the path"""
        random_file_name = os.urandom(8).hex() + ".test"
        random_file_path = pl.Path.joinpath(path, random_file_name)
        self.random_files_list.append(random_file_path)
        with open(random_file_path, 'wb') as new_file:
            new_file.write(os.urandom(1024))
        return random_file_path
