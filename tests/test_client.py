import unittest
import pathlib as pl
from time import sleep

import globals
from client import Client
import os


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = Client()
        self.sleep_time = 1
        self.random_files_list = []

    def test_created_file_is_uploaded(self):
        """Create a new random file and place it in files folder for upload"""
        random_file_path = self.create_random_file().relative_to(globals.WORK_DIR)
        sleep(self.sleep_time)
        file_list_enc = self.client.servercoms.get_file_list()
        file_list_dec = self.client.file_crypt.decrypt_file_list(file_list_enc)
        self.assertIn(random_file_path, file_list_dec)

    def test_delete_file(self):
        """Create file, delete it, check if it is deleted on server"""
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        sleep(1)
        pl.Path.unlink(random_file_path)
        self.random_files_list.remove(random_file_path)
        sleep(self.sleep_time)
        self.assertNotIn(random_file_relative_path, self.client.get_local_file_list())
        file_list_enc = self.client.servercoms.get_file_list()
        file_list_dec = self.client.file_crypt.decrypt_file_list(file_list_enc)
        self.assertNotIn(random_file_relative_path, file_list_dec)

    def test_retrieve_file_from_server(self):
        """Create new file, make sure it is uploaded, delete it locally, get it back"""
        # Create file, wait, check if it was uploaded
        random_file_path = self.create_random_file()
        random_file_relative_path = random_file_path.relative_to(globals.WORK_DIR)
        random_file_name = pl.Path(random_file_path.name)
        sleep(self.sleep_time)
        file_list_enc = self.client.servercoms.get_file_list()
        file_list_dec = self.client.file_crypt.decrypt_file_list(file_list_enc)
        self.assertIn(random_file_relative_path, file_list_dec)
        # Delete the file locally, "close client" such that the server is not asked to also delete (archive)
        self.client.close_client()
        sleep(0.2)
        pl.Path.unlink(random_file_path)
        self.assertNotIn(random_file_name, self.client.get_local_file_list())
        # Get file back, make sure we got it
        self.client.get_file(random_file_relative_path)
        sleep(self.sleep_time)
        self.assertIn(random_file_relative_path, self.client.get_local_file_list())

    def tearDown(self):
        self.client.start_observing()
        for file in self.random_files_list:
            if pl.Path.exists(file):
                pl.Path.unlink(file)
        globals.clear_tmp()
        self.client.close_client()

    def create_random_file(self, path=globals.FILE_FOLDER):
        """Create a random file in the file folder, give back the path"""
        random_file_name = os.urandom(8).hex()
        random_file_path = pl.Path.joinpath(path, random_file_name)
        self.random_files_list.append(random_file_path)
        with open(random_file_path, 'wb') as new_file:
            new_file.write(os.urandom(1024))
        return random_file_path
