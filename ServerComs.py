import os
import requests

import globals


class ServComs():
    """Communicates with the file-host server"""
    # ToDO: Do we even have a connection ?

    def __init__(self, serverIP):
        self.serverLocation = serverIP
        self.cert = "wyrnasmyqnapcloudcom.crt"
        self.verify = False #self.cert

    def send_file(self, file_path):
        """Send provided filename to the server"""
        # ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        with open(file_path, 'rb') as file:
            response = requests.post('https://' + self.serverLocation + '/upload_file', files={'file': file}, verify=self.verify)
        return response

    def get_file(self, file_path):
        # ToDo: does server even have the file ? (otherwise empty file)
        """Retrive file_name from server and place it in tmp (ready for decryption)"""
        file_name = file_path.split("\\")[-1]
        tmp_file_location = os.path.join(globals.TEMPORARY_FOLDER, file_name)
        response = requests.get('https://' + self.serverLocation + '/get_file/' + file_name, verify=self.verify)
        with open(tmp_file_location, "wb") as saveFile:
            saveFile.write(response.content)
        return response, tmp_file_location

    def get_file_list(self):
        """Get a list of what files the server has"""
        response = requests.get('https://' + self.serverLocation + '/list_files', verify=self.verify)
        return response

    # Todo: rename file
    # Todo: delete file

