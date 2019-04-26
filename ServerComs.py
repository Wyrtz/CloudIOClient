import json
import pathlib as pl
from json import JSONDecodeError

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

from resources import globals


class ServComs():
    """Communicates with the file-host server"""
    # ToDO: Do we even have a connection ?

    def __init__(self, serverIP):
        self.serverLocation = serverIP
        self.cert = "wyrnasmyqnapcloudcom.crt"
        self.verify = False  #self.cert

    def send_file(self, file_path, additional_data, userID):
        """Send provided filename to the server"""
        # ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        with open(file_path, 'rb') as file:
            response = requests.post('https://' + self.serverLocation + '/upload_file/' + userID,
                                     files={'file_content': file,
                                            'additional_data': bytes(json.dumps(additional_data), 'utf-8')},
                                     verify=self.verify)
            response.raise_for_status()
            return True  # TODO: Check if redundant? see send file in client

    def get_file(self, enc_file_name, userID):
        """Retrive enc_file_name from server and place it in tmp (ready for decryption)"""
        response = requests.get('https://' + self.serverLocation + '/get_file/' + enc_file_name + '/' + userID, verify=self.verify)
        if response.status_code == 404:
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

    def get_file_list(self, userID: str):
        """Get a list of what files the server has"""
        response = requests.get('https://' + self.serverLocation + '/list_files/' + userID, verify=self.verify)
        response.raise_for_status()
        try:
            response_dict = json.loads(response.content)
        except JSONDecodeError:
            raise FileNotFoundError  # TODO: Replace this error?
        if 'file_list' not in response_dict.keys():
            raise FileNotFoundError  # TODO: Replace this error?
        enc_file_list_with_nonces = response_dict['file_list']
        return enc_file_list_with_nonces

    # Todo: rename file: Send delete file request (and send the renamed file)
    # Todo: delete file

    def register_deletion_of_file(self, enc_file_name, userID):
        """Signals to server that the file known by its encrypted alias should not be considered 'live' anymore."""
        response = requests.post(
            'https://' + self.serverLocation + '/archive_file/' + str(enc_file_name) + '/' + userID,
            verify=self.verify
        )
        if response.status_code != 404:
            response.raise_for_status()
        else:
            print("File not on server")
        print("File archived on server")
        # TODO: Consider adding upload verification?