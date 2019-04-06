import os
import pathlib as pl
import platform
from threading import Thread
from time import sleep, time
from watchdog.events import FileSystemEventHandler
from ServerComs import ServComs
from filecryptography import FileCryptography
from watchdog.observers import Observer
from pyfiglet import Figlet
import globals


class MyHandler(FileSystemEventHandler):
    """Custom Handling FileSystemEvents"""

    def __init__(self, servercoms: ServComs, file_crypt: FileCryptography, client):
        self.servercoms = servercoms
        self.file_crypt = file_crypt
        self.client = client

    def on_any_event(self, event):
        """Print any received event to console"""
        # print(f'event type: {event.event_type}  path : {event.src_path}')
        pass

    def on_created(self, event):
        """Send newly created file to the server"""
        file_path = pl.Path(event.src_path)
        relative_file_path = file_path.relative_to(globals.WORK_DIR)
        print("File created: " + str(relative_file_path))
        if relative_file_path in globals.DOWNLOADED_FILE_QUEUE:
            globals.DOWNLOADED_FILE_QUEUE.remove(relative_file_path)
            return
        self.client.send_file(file_path)

    def on_deleted(self, event):
        abs_path = pl.Path(event.src_path)
        relative_path = abs_path.relative_to(globals.WORK_DIR)
        print("File deleted: " + str(relative_path))
        enc_file_name = self.file_crypt.encrypt_relative_file_path(relative_path)
        self.servercoms.register_deletion_of_file(enc_file_name)


class Client:

    def __init__(self, server_location=globals.SERVER_LOCATION, file_folder=globals.FILE_FOLDER):
        self.server_location = server_location
        self.file_folder = file_folder
        self.servercoms = ServComs(server_location)
        self.file_crypt = FileCryptography()
        self.handler_thread = Thread(target=MyHandler, args=(self.servercoms, self.file_crypt, self))
        self.handler_thread.start()
        # Start initial folder observer
        self.observers_list = []
        self.start_observing()

    def start_observing(self):
        self.start_new_folder_observer(self.file_folder)

    def start_new_folder_observer(self, file_folder_path):
        new_observer = Observer()
        handler = MyHandler(self.servercoms, self.file_crypt, self)
        new_observer.schedule(handler, str(file_folder_path), recursive=True)
        self.observers_list.append(new_observer)
        new_observer.start()

    def send_file(self, file_path):
        try:
            enc_file_path, additional_data = self.file_crypt.encrypt_file(file_path)
            self.servercoms.send_file(enc_file_path, additional_data)
        except PermissionError:
            print("Unable to send file immediately...")
            sleep(1)
            self.send_file(file_path)
            return
        pl.Path.unlink(enc_file_path)  # Delete file

    def get_file(self, file_name):
        """Encrypt the name, send a request and get back either '404' or a file candidate.
           If the candidate is valid and newer, keep it."""
        enc_file_name = self.file_crypt.encrypt_relative_file_path(file_name)
        try:
            tmp_enc_file_path, additional_data = self.servercoms.get_file(str(enc_file_name))
        except FileNotFoundError:
            print("File not found on server.")
            return
        self.file_crypt.decrypt_file(tmp_enc_file_path,  # TODO: If doesn't validate, does it overwrite?
                                     additional_data=additional_data)
        os.remove(tmp_enc_file_path)

    def get_local_file_list(self):
        """Return a list where each element is the string name of this file"""
        # ToDo: recursive (folders)
        # ToDO: PathLib? No os.listdir function
        file_list = os.listdir(self.file_folder)
        file_list = [pl.Path(x) for x in file_list]
        file_list = [pl.Path.joinpath(globals.FILE_FOLDER, x) for x in file_list]
        file_list = [x.relative_to(globals.WORK_DIR) for x in file_list]
        return file_list

    def sync_files(self):  # TODO: Refactor this.
        local_file_list = client.get_local_file_list()
        enc_remote_file_list = client.servercoms.get_file_list()
        dec_remote_file_list = client.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x) for x in dec_remote_file_list]
        files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list)
        files_not_on_client = globals.get_list_difference(pathlib_remote_file_list, local_file_list)
        for file in files_not_on_server:
            self.send_file(file)
        for file in files_not_on_client:
            self.get_file(file)

    def close_client(self):
        """Close all observers observing a folder"""
        for observer in self.observers_list:
            observer.stop()
        for observer in self.observers_list:
            observer.join()


def start_user_interface():
    figlet = Figlet()
    try:
        # clear_screen()
        # username = input("Username:")
        # password = input("Password:")
        # clear_screen()
        # welcome = "Welcome " + username + " !"
        # print(figlet.renderText(welcome))
        # sleep(1.5)
        clear_screen()
        while True:
            command = input("Command:")
            command = command.lower()
            clear_screen()
            if command == "h" or command == "help":
                print(get_help())
            if command == "sync" or command == "s":
                print("Syncing...")
                client.sync_files()
            if command == "ls" or command == "lf" or command == "local files":
                print("Local files:")
                print_local_files()
            if command == "rf" or command == "remote files":
                print("Remote files:")
                print_remote_files()
            if command == "gf" or command == "get file":
                print("getting file...")
                print("(not implemented)")
            if command == "diff" or command == "d":
                print_diff_to_server()
            if command == 'exit' or command == 'e':
                client.close_client()
                clear_screen(print_logo=False)
                break
            else:
                print(get_help())

    except KeyboardInterrupt:
        clear_screen(print_logo=False)
        client.close_client()


def print_list(list_to_print):
    for element in list_to_print:
        print("\t", element)


def print_remote_files():
    enc_remote_file_list = client.servercoms.get_file_list()
    if len(enc_remote_file_list) == 0:
        print("\t(no files on server)")
    else:
        dec_remote_file_list = client.file_crypt.decrypt_file_list(enc_remote_file_list)
        print_list(dec_remote_file_list)


def print_local_files():
    local_file_list = client.get_local_file_list()
    if len(local_file_list) == 0:
        print("\t(no files locally)")
    else:
        print_list(local_file_list)

def print_diff_to_server():
    local_file_list = client.get_local_file_list()
    enc_remote_file_list = client.servercoms.get_file_list()
    dec_remote_file_list = client.file_crypt.decrypt_file_list(enc_remote_file_list)
    pathlib_remote_file_list = [pl.Path(x) for x in dec_remote_file_list]
    files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list)
    files_not_on_client = globals.get_list_difference(pathlib_remote_file_list, local_file_list)
    print("Difference:")
    if len(files_not_on_client) == 0:
        print("\tClient up to date")
    else:
        print("Files not on client:")
        print_list(files_not_on_client)
    if len(files_not_on_server) == 0:
        print("\tServer up to date")
    else:
        print("Files not on server:")
        print_list(files_not_on_server)

def clear_screen(print_logo=True):
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')
    if print_logo:
        figlet = Figlet()
        print(figlet.renderText(globals.PROJECT_NAME))


def get_help():
    help = """
Available commands:
    Help (h, help)
    Sync (s, sync)
    Local_files (ls, lf, local files)
    Remote_files (rf, remote files)
    Get_file (gf, get file)
    Diff_local/remote (diff, d)
    Exit (e, exit)
                    """
    return help


if __name__ == "__main__":
    serverIP = 'wyrnas.myqnapcloud.com:8000'
    client = Client(serverIP)
    start_user_interface()

