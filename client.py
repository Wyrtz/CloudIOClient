import os
from threading import Thread
from time import sleep
from watchdog.events import FileSystemEventHandler
from ServerComs import ServComs
from file_cryptography import file_cryptography
from folder_watcher import folder_watcher
import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""
    #ToDo: handle creations properly.

    def __init__(self, servercoms, file_crypt):
        self.servercoms = servercoms
        self.file_crypt = file_crypt

    def on_any_event(self, event):
        """Print any received event to console"""
        print(f'event type: {event.event_type}  path : {event.src_path}')

    def on_created(self, event):
        """Send newly created file to the server"""
        file_name = event.src_path.split("/")[1]
        response = None
        enc_file_name = ""
        file_path = os.path.join(globals.FILE_FOLDER, file_name)
        if file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(file_path)
            print("Removed ", file_path, "from queue")
            return
        try:
            enc_file_name = self.file_crypt.encrypt_file(file_path)
            response = self.servercoms.send_file(enc_file_name)
        except PermissionError:
            print("failed once")
            sleep(5)
            self.on_created(event)
            return
        if response.status_code == 200:
            os.remove(enc_file_name)
        # print("Send file")
        # sleep(3)
        # print("Delete file")
        # os.remove(file_path)
        # sleep(3)
        # print("Get file")
        # _, enc_file_path = self.servercoms.get_file(enc_file_name)
        # dec_file_path = self.file_crypt.decrypt_file(enc_file_path)


class client():

    def __init__(self, serverIP, folder="files"):
        self.serverIP = serverIP
        self.folder = folder
        self.servercoms = ServComs(serverIP)
        self.file_crypt = file_cryptography()
        self.handler = MyHandler(self.servercoms, self.file_crypt)
        folder_watcher_thread = Thread(target=folder_watcher, args=(folder + "/", self.handler))
        folder_watcher_thread.start()
        #self.folder_watcher = folder_watcher(folder + "/", self.handler)
        #self.sync_files()

    def get_folder_list(self):
        """Return a list where each element is the string name of this file"""
        # ToDo: recursive (folders)
        files = os.listdir(self.folder + "/")
        file_list = []
        for name in files:
            file_list.append(name)
        return file_list

    def sync_files(self):
        response = self.servercoms.get_file_list()
        print(response)
        server_files = list(response.json())
        client_files = self.get_folder_list()
        print("server files: ", server_files)
        print("client_files", client_files)
        # for remote_file in server_files:
        #     if remote_file not in client_files:
        #         self.servercoms.get_file(remote_file)
        #todo: FINNISH THIS!
        #todo: Test this!
        #todo: handle file not found, no connection etc. !

    def get_file(self, enc_file_name):
        _, enc_file_path = self.servercoms.get_file(enc_file_name)
        dec_file_path = self.file_crypt.decrypt_file(enc_file_path)
        os.remove(enc_file_path)



if __name__ == "__main__":
    serverIP = 'wyrnas.myqnapcloud.com:8000'
    client = client(serverIP)

