import os
import pathlib as pl
import shutil
import unittest
from time import sleep

import requests

import client
from client import Client
from resources import globals
from security import keyderivation
from tests import setup_test_environment as ste


class TestClient(unittest.TestCase):
    """Class for unittesting the client.py module"""

    def unregister_user(self, userID: str) -> None:
        """
        Method for unregistering (test) users when done testing
        Args:
            userID: The ID of the user to unregister on the server
        """
        requests.post('https://' + self.serverIp + '/unregister/' + userID, verify=False)

    def setUp(self):
        self.serverIp = 'wyrnas.myqnapcloud.com:8001'  # '127.0.0.1:443'
        self.sleep_time = 3
        self.random_files_list = []
        self.username = "abecattematteman"
        self.pw = '1234567890101112'
        self.kd = keyderivation.KeyDerivation(self.username)
        self.ste = ste.global_test_configer(self.kd)
        self.file_crypt = self.kd.select_first_pw(self.pw)
        self.client = Client(username=self.username, password=self.pw, server_location=self.serverIp)

    def tearDown(self):
        self.client.close_observers()
        self.ste.recover_resources()
        notDone = True
        while notDone:
            try:
                for file in self.random_files_list:
                    if pl.Path.exists(file):
                        if pl.Path.is_dir(file):
                            pl.Path.rmdir(file)
                        else:
                            pl.Path.unlink(file)
            except PermissionError:
                sleep(0.1)
                continue
            notDone = False
        globals.clear_tmp()
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
        """Test the ability to backup a key and then restore the key with the shares"""
        shares = self.client.backup_key(self.pw, 10, 20)
        self.assertTrue(len(shares) == 20)
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[:9], self.username, 'wertyuisdfgh')
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[5:9], self.username, 'wertyuisdfgh')
        self.assertRaises(AssertionError, client.replace_key_from_backup, shares[5:14], self.username, 'wertyuisdfgh')
        new_pw = 'wertyuiosdfghj'
        client.replace_key_from_backup(shares[3:15], self.username, new_pw)
        self.client.kd.derive_key(new_pw)

    def test_replacing_pw_syncs_files(self):
        """Test that replacing the passwords makes all the files available under the new password (they are synced)"""
        l1 = list(globals.SERVER_FILE_DICT)
        self.assertTrue(l1 == [])
        rand_path1 = self.create_random_file().relative_to(globals.WORK_DIR)
        rand_path2 = self.create_random_file().relative_to(globals.WORK_DIR)
        rand_path3 = self.create_random_file().relative_to(globals.WORK_DIR)
        sleep(self.sleep_time)

        l2 = list(globals.SERVER_FILE_DICT)
        for path in [rand_path1, rand_path2, rand_path3]:
            self.assertIn(path, l2)
        self.assertTrue(len(l2) == 3)
        new_pw = 'qwertyuiokjhgfdsghjhg'
        self.client.replace_password(self.pw, new_pw)
        l3 = list(globals.SERVER_FILE_DICT)
        for path in [rand_path1, rand_path2, rand_path3]:
            self.assertIn(path, l3)

    def test_filecrypt_and_servcoms_of_primary_key_is_retrievable(self):
        """Test that a random path of a file leads to the default servercoms/filecrypt pair"""
        some_path = globals.FILE_FOLDER.joinpath('something').relative_to(globals.WORK_DIR)
        self.assertTrue('files/something' == some_path.as_posix(),
                        'expected "files/something" but was ' + some_path.as_posix())
        filecrypt, servcoms = self.client.get_file_crypt_servercoms(some_path)  # Default
        self.assertTrue(filecrypt == self.client.file_crypt)
        self.assertTrue(servcoms == self.client.servercoms)

    def test_filecrypt_and_servcoms_of_shared_key_is_retrievable(self):
        """
        Tests to see if, when we have created a folder to be shared, that when retrieving servcoms and filecrypt
        for the folder that we retrieve some that aren't default and that the servcoms is that of the shared key.
        """
        key = globals.generate_random_key()  # Get a random key
        test_folder_name = pl.Path('test')
        test_folder_abs_path = globals.FILE_FOLDER.joinpath(test_folder_name)
        self.random_files_list.append(test_folder_abs_path)  # 4 teardown - remove the folder
        test_folder_rel_path = test_folder_abs_path.relative_to(globals.WORK_DIR)
        self.client.create_shared_folder(test_folder_name, key)  # create the folder to be shared
        self.assertEqual(test_folder_rel_path, pl.Path('files/test'))  # path is what we expect?
        filecrypt, servcoms = self.client.get_file_crypt_servercoms(test_folder_rel_path)
        self.assertFalse(filecrypt == self.client.file_crypt)  # Not default
        self.assertFalse(servcoms == self.client.servercoms)  # Not default
        self.assertTrue(servcoms.userID == client.hash_key_to_userID(key))  # Correct ID

    def test_shared_folders_use_the_right_key(self):
        """Ensure that a new shared folder encrypts new files under the new key"""
        key = globals.generate_random_key()  # Get a random key
        test_folder_name = pl.Path('test')
        test_folder_abs_path = globals.FILE_FOLDER.joinpath(test_folder_name)
        test_folder_rel_path = test_folder_abs_path.relative_to(globals.WORK_DIR)
        self.client.create_shared_folder(test_folder_name, key)  # create the folder to be shared
        random_file_abs_path = self.create_random_file(test_folder_abs_path)
        self.random_files_list.append(test_folder_abs_path)  # for teardown - remove the folder
        filecrypt, servcoms = self.client.get_file_crypt_servercoms(test_folder_rel_path)
        sleep(self.sleep_time)
        file_list = servcoms.get_file_list()
        self.assertEqual(len(file_list), 1)
        enc_rel_path, nonce, _ = file_list[0]
        retrieved_rel_path = filecrypt.decrypt_relative_file_path(enc_rel_path, bytes.fromhex(nonce))
        self.assertEqual(retrieved_rel_path, random_file_abs_path.relative_to(globals.WORK_DIR))

    def test_can_add_shared_folder(self):
        """Test the ability for another client to get the files from a shared folder"""
        share_key = globals.generate_random_key()  # Get a random key
        test_folder_name = pl.Path('test')
        test_folder_abs_path = globals.FILE_FOLDER.joinpath(test_folder_name)
        test_folder_rel_path = test_folder_abs_path.relative_to(globals.WORK_DIR)
        client1 = self.client
        client1.create_shared_folder(test_folder_name, share_key)
        random_file_abs_path = self.create_random_file(test_folder_abs_path)
        self.random_files_list.append(test_folder_abs_path)  # 4 teardown - remove the folder
        # close down first client
        sleep(self.sleep_time)
        client1.close_observers()

        pl.Path.unlink(random_file_abs_path)  # Remove the file ...
        pl.Path.rmdir(test_folder_abs_path)   # ... and dir to emulate new client.

        other_username = 'sdfghjkytredefwsdf'
        other_pw = 'sfghjkluytsdfsgrwqe'
        kd = keyderivation.KeyDerivation(other_username)
        key_client2 = kd.derive_key(other_pw, False)
        kd.store_hash_of_key(key_client2)  # Now we're another client
        globals.SHARED_KEYS.unlink()

        client2 = Client(other_username, other_pw)
        client2.add_share_key(share_key)
        filecrypt, servcoms = client2.get_file_crypt_servercoms(test_folder_rel_path)
        self.assertNotEqual(client2.file_crypt, filecrypt)  # Not defaulting
        self.assertNotEqual(client2.servercoms, servcoms)   # Not defaulting
        self.assertTrue(pl.Path.exists(random_file_abs_path))  # Got the shared file (and thereby folder).
        client2.close_observers()

    def test_shared_folders_persist(self):
        """Test that shared folder (keys) are not lost when closing the client"""
        key = globals.generate_random_key()
        folder_name = pl.Path('forglem_mig_ai')
        test_folder_abs_path = globals.FILE_FOLDER.joinpath(folder_name)
        self.random_files_list.append(test_folder_abs_path)  # 4 teardown - remove the folder
        # Create the shared folder
        self.client.create_shared_folder(folder_name, key)
        dict1 = self.client.folder_to_file_crypt_servercoms_dict

        self.client.close_observers()

        client2 = Client(self.username, self.pw)
        dict2 = client2.folder_to_file_crypt_servercoms_dict
        client2.close_observers()
        self.assertEqual(dict1, dict2, "Expect new client instance to have loaded the previous client's dict.")

    def create_random_file(self, path: pl.Path = globals.FILE_FOLDER) -> pl.Path:
        """Create a random file in the file folder, give back the path

        Args:
            path: where to place the random file (default= files folder)

        Returns:
            pl.Path: the path of the just created random file
        """
        random_file_name = os.urandom(8).hex() + ".test"
        random_file_path = pl.Path.joinpath(path, random_file_name)
        self.random_files_list.append(random_file_path)
        with open(random_file_path, 'wb') as new_file:
            new_file.write(os.urandom(1024))
        return random_file_path
