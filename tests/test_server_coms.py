import unittest
import os

from ServerComs import ServComs


class TestServercoms(unittest.TestCase):
    def setUp(self):
        self.serverIp = '10.192.0.184'
        self.folder = '../files'
        # ../ files / pic1.png
        self.serverComs = ServComs(self.serverIp, self.folder)
        self.file_name = "pic1.png"

    def test_send_file(self):
        file_name = self.file_name
        response = self.serverComs.send_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200, "Tried to send file " + file_name)

    def test_receive_send_file(self):
        #Send file
        file_name = self.file_name
        file_path = self.folder + "/" + file_name
        send_file_size = os.stat(file_path).st_size
        response = self.serverComs.send_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200, "Tried to send file " + file_name)
        #Get it back
        response = self.serverComs.get_file(file_name)
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200, "Tried to recieve file " + file_name)
        #Make sure the file we got back has the same conten as the one we send (aproxx)
        recv_file_size = os.stat(file_path).st_size
        self.assertEqual(send_file_size, recv_file_size, "Files differs in size!")


    def test_get_file_list(self):
        response = self.serverComs.get_file_list()
        self.assertNotIsInstance(response, type(None), "Got no response back!")
        self.assertEqual(response.status_code, 200)
        jsonRe = response.json()
        self.assertIn("pic1.png", jsonRe)


if __name__ == '__main__':
    unittest.main()
