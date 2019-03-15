import json
import unittest
import filecmp

from client import ServComs


class TestClient(unittest.TestCase):
    def setUp(self):
        serverIp = '192.168.1.79'
        self.serverComs = ServComs(serverIp)
        self.file_name = "pic1.png"

    def test_send_file(self):
        file_name = self.file_name
        response = self.serverComs.send_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)

    def test_receive_send_file(self):
        #Send file
        file_name = self.file_name
        rec_file_name = "files/back.png"
        response = self.serverComs.send_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)
        #Get it back
        file_name = self.file_name
        response = self.serverComs.get_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)
        #Make sure the file we got back has the same conten as the one we send
        self.assertEqual(filecmp.cmp(rec_file_name, ("files/" + file_name)), True, "Files differs!")


    def test_get_file_list(self):
        response = self.serverComs.get_file_list()
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)
        jsonRe = response.json()
        self.assertIn("pic1.png", jsonRe)


if __name__ == '__main__':
    unittest.main()
