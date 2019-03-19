import requests

class ServComs():

    def __init__(self, serverIP, folder):
        self.serverLocation = serverIP
        self.folder = folder + '/'

    def send_file(self, file_name):
        #ToDo: send as stream for big files (otherwise memory error). Tested up to 300mb works
        #Todo: handle failed uploads
        with open(self.folder + file_name, 'rb') as file:
            response = requests.post('https://' + self.serverLocation + '/upload_file', files={'file': file}, verify=False)
        return response

    def get_file(self, file_name):
        response = requests.get('https://' + self.serverLocation + '/get_file/' + file_name, verify=False)
        with open(self.folder + file_name, "wb") as saveFile:
            saveFile.write(response.content)
        return response

    def get_file_list(self):
        response = requests.get('https://' + self.serverLocation + '/list_files', verify=False)
        return response

    #Todo: rename file

