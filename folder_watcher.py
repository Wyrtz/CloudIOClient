import os
import time
from watchdog.observers import Observer



class folder_watcher:
    def __init__(self, path, handler):
        self.path = path
        event_handler = handler
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
