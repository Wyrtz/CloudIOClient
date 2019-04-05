import unittest
import pathlib as pl
import globals
from client import Client


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = Client()
        self.file_name = "pic1.jpg"
        self.file_path = pl.Path.joinpath(globals.TEST_FILE_FOLDER, self.file_name)
        self.relative_file_path = self.file_path.relative_to(globals.WORK_DIR)

    def test_created_file_is_uploaded(self):
        # Get file list from server, check file is not there already
        start_file_list_enc = self.client.servercoms.get_file_list()
        start_file_list_dec = self.client.file_crypt.decrypt_file_list(start_file_list_enc)

        print(start_file_list_dec)
        print(self.relative_file_path)
        print(self.relative_file_path in start_file_list_dec)
        # print(start_file_list_enc)

        # Create file
        # Get file list from server, check the file is now there

        # print("Send file")
        # sleep(3)
        # print("Delete file")
        # os.remove(file_path)
        # sleep(3)
        # print("Get file")
        # _, enc_file_path = self.servercoms.get_file(enc_file_name)
        # dec_file_path = self.file_crypt.decrypt_file(enc_file_path)

    def tearDown(self):
        print("Mister Watchdog")
        self.client.close_client()
        globals.clear_tmp()
