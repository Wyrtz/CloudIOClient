## Connect modules ##
from time import sleep

from watchdog.events import FileSystemEventHandler
from ServerComs import ServComs
from folder_watcher import folder_watcher


class MyHandler(FileSystemEventHandler):

    def __init__(self, servercoms):
        self.servercoms = servercoms

    def on_any_event(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')

    def on_created(self, event):
        file_name = event.src_path.split("/")[1]
        response = None
        try:
            response = self.servercoms.send_file(file_name)
        except PermissionError:
            print("failed once")
            sleep(5)
            self.on_created(event)
        if response:
            print(response)

if __name__ == "__main__":
    serverIP = '10.192.0.184'
    folder = 'files'
    servercoms = ServComs(serverIP, folder)
    handler = MyHandler(servercoms)
    path = "files/"
    folder_watcher = folder_watcher(path, handler)


