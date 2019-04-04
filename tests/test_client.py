import unittest
from client import client


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = client()

    def test_created_file_is_uploaded(self):
        # Get file list from server, check file is not there already
        start_file_list = client.servercoms.get_file_list()
        print(start_file_list)
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
