import requests

class ServComs():
    """Communicates with the file-host server"""
    #ToDO: Do we even have a connection ?

    def __init__(self, serverIP, folder):
        self.serverLocation = serverIP
        self.folder = folder + '/'

    def send_file(self, file_name):
        """Send provided filename to the server"""
        #ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        #Todo: handle failed uploads
        with open(self.folder + file_name, 'rb') as file:
            response = requests.post('http://' + self.serverLocation + '/upload_file', files={'file': file}, verify=False)
        return response

    def get_file(self, file_name):
        """Retrive file_name from server"""
        response = requests.get('http://' + self.serverLocation + '/get_file/' + file_name, verify=False)
        with open(self.folder + file_name, "wb") as saveFile:
            saveFile.write(response.content)
        return response

    def get_file_list(self):
        """Get a list of what files the server has"""
        response = requests.get('http://' + self.serverLocation + '/list_files', verify=False)
        return response

    #Todo: rename file

