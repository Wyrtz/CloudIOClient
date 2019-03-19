import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MyHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')

class folder_watch:
    def __init__(self, path):
        self.path = path
        event_handler = MyHandler()
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def get_folder_list(self):
        files = os.listdir(self.path)
        file_list = []
        for name in files:
            file_list.append(name)
        return file_list
