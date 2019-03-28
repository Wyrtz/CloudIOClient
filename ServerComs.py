import requests

class ServComs():
    """Communicates with the file-host server"""
    #ToDO: Do we even have a connection ?

    def __init__(self, serverIP):
        self.serverLocation = serverIP
        self.cert = "wyrnasmyqnapcloudcom.crt"
        self.verify = False #self.cert

    def send_file(self, file_path):
        """Send provided filename to the server"""
        #ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        #Todo: handle failed uploads
        with open(file_path, 'rb') as file:
            response = requests.post('https://' + self.serverLocation + '/upload_file', files={'file': file}, verify=self.verify)
        return response

    def get_file(self, file_path):
        """Retrive file_name from server and place it in tmp (ready for decryption)"""
        file_name = file_path.split("\\")[-1]
        response = requests.get('https://' + self.serverLocation + '/get_file/' + file_name, verify=self.verify)
        with open(file_path, "wb") as saveFile:
            saveFile.write(response.content)
        return response

    def get_file_list(self):
        """Get a list of what files the server has"""
        response = requests.get('https://' + self.serverLocation + '/list_files', verify=self.verify)
        return response

    #Todo: rename file

