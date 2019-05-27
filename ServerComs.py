import json
import pathlib as pl
from json import JSONDecodeError

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

from resources import globals
from hashlib import sha3_224


class ServComs():
    """Communicates with the file-host server"""
    # ToDO: Do we even have a connection?

    def __init__(self, serverIP: str, userID: str):
        """
        Args:
            serverIP: the location of the server we try to connect to
            userID: the ID to forward to the server whenever making a request
        """
        self.serverLocation = serverIP
        self.userID = userID
        self.cert = "wyrnasmyqnapcloudcom.crt"
        self.verify = False  #self.cert
        self.register_user()

    def __hash__(self):
        hasher: sha3_224 = sha3_224()
        hasher.update(bytes(self.serverLocation, "utf-8"))
        hasher.update(bytes(self.userID, "utf-8"))
        hasher.update(bytes(self.cert, "utf-8"))
        return hasher.digest().hex()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.__hash__() == other.__hash__()

    def send_file(self, file_path: pl.Path, additional_data: dict) -> None:
        """Send provided filename to the server

        Args:
            file_path: the path of the file to send
            additional_data: the additional data (nonce, time +) for the file
        """
        # ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        with open(file_path, 'rb') as file:
            response = requests.post('https://' + self.serverLocation + '/upload_file/' + self.userID,
                                     files={'file_content': file,
                                            'additional_data': bytes(json.dumps(additional_data), 'utf-8')},
                                     verify=self.verify)
            response.raise_for_status()

    def get_file(self, enc_file_name: str):
        """
        Retrive enc_file_name from server and place it in tmp (ready for decryption)

        Args:
            enc_file_name: the (encrypted) name wanted from the server
        """
        response = requests.get('https://' + self.serverLocation + '/get_file/' + enc_file_name + '/' + self.userID, verify=self.verify)
        if response.status_code != 404:
            response.raise_for_status()
        else:
            raise FileNotFoundError
        try:
            # should be dict of {file->file, additional_data->additional_data}
            response_dict = json.loads(response.content)
        except JSONDecodeError:
            raise FileNotFoundError  # Bad JSON?
        if 'file' not in response_dict.keys() or 'additional_data' not in response_dict.keys():
            raise FileNotFoundError  # If the server provides garbage we throw it in the trash.
        tmp_file_location = pl.PurePath.joinpath(globals.TEMPORARY_FOLDER, enc_file_name)
        with open(tmp_file_location, "wb") as saveFile:  # Assume it's the file we requested.
            saveFile.write(bytes.fromhex(response_dict['file']))
        return tmp_file_location, response_dict['additional_data']

    def get_file_list(self) -> list:
        """Get a list of what files the server has

        Returns:
            list: a list of lists where each sublist contains the encrypted name, the nonce and timestamp of each file
        """
        response = requests.get('https://' + self.serverLocation + '/list_files/' + self.userID, verify=self.verify)
        try:
            response_dict = json.loads(response.content)
        except JSONDecodeError:
            raise FileNotFoundError  # TODO: Replace this error?
        if 'file_list' not in response_dict.keys():
            raise FileNotFoundError  # TODO: Replace this error?
        enc_file_list_with_nonces_and_timestamp = response_dict['file_list']
        return enc_file_list_with_nonces_and_timestamp

    def rename_file(self, enc_file_name_previous: pl.Path, new_file_path: pl.Path, new_additional_data: dict) -> None:
        """
        NOT implemented, do not use!
        Args:
            enc_file_name_previous: The current encrypted filename
            new_file_path: The new name to rename into on the server
            new_additional_data: assosiated data with the new file path
        """
        self.register_deletion_of_file(enc_file_name_previous)
        self.send_file(new_file_path, new_additional_data)

    def register_deletion_of_file(self, enc_file_name: pl.Path):
        """
        Signals to server that the file known by its encrypted alias should not be considered 'live' anymore.

        Args:
            enc_file_name: The (encrypted) name of the file to be deleted on the server
        """
        response = requests.post(
            'https://' + self.serverLocation + '/archive_file/' + str(enc_file_name) + '/' + self.userID,
            verify=self.verify
        )
        if response.status_code != 404:
            response.raise_for_status()
        else:
            print("Warning; file not on server attempted to be archived: " + enc_file_name)

    def register_user(self):
        """Register a new user on the server"""
        response = requests.post('https://' + self.serverLocation + '/register/' + self.userID, verify=False)

        if response.status_code != 400: # User already registered
            response.raise_for_status()
