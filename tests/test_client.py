import unittest
import pathlib as pl
from time import sleep

import globals
from client import Client
import os


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = Client()
        self.sleep_time = 2
        self.random_files_list = []

    def test_created_file_is_uploaded(self):
        # Create a new random file and place it in files folder for upload
        random_file_path = self.create_random_file().relative_to(globals.WORK_DIR)
        sleep(self.sleep_time)
        file_list_enc = self.client.servercoms.get_file_list()
        file_list_dec = self.client.file_crypt.decrypt_file_list(file_list_enc)
        self.assertIn(random_file_path, file_list_dec)

    def test_delete_files(self):
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        sleep(0.5)
        pl.Path.unlink(random_file_path)
        self.random_files_list.remove(random_file_path)
        sleep(self.sleep_time)
        file_list_enc = self.client.servercoms.get_file_list()
        file_list_dec = self.client.file_crypt.decrypt_file_list(file_list_enc)
        self.assertNotIn(random_file_relative_path, file_list_dec)

    def tearDown(self):
        self.client.close_client()
        globals.clear_tmp()
        for file in self.random_files_list:
            pl.Path.unlink(file)

    def create_random_file(self):
        random_file_name = os.urandom(8).hex()
        random_file_path = pl.Path.joinpath(globals.FILE_FOLDER, random_file_name)
        self.random_files_list.append(random_file_path)
        with open(random_file_path, 'wb') as new_file:
            new_file.write(os.urandom(1024))
        return random_file_path