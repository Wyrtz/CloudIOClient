import requests

class ServComs():

    def __init__(self, serverIP):
        self.serverLocation = serverIP

    def send_file(self, file_name):
        with open('files\\' + file_name, 'rb') as file:
            response = requests.post('http://' + self.serverLocation + '/upload_file', files={'file': file})
        return response

    def get_file(self, file_name):
        response = requests.get('http://' + self.serverLocation + '/get_file/' + file_name)
        with open("files/" + file_name, "wb") as saveFile:
            saveFile.write(response.content)
        return response

    def get_file_list(self):
        response = requests.get('http://' + self.serverLocation + '/list_files')
        return response

