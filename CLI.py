import os
import platform

from pyfiglet import Figlet

import globals
import pathlib as pl


class CLI:

    def __init__(self, client):
        from client import Client
        self.client = client
        self.start_user_interface()

    def start_user_interface(self):
        figlet = Figlet()
        try:
            # clear_screen()
            # username = input("Username:")
            # password = input("Password:")
            # clear_screen()
            # welcome = "Welcome " + username + " !"
            # print(figlet.renderText(welcome))
            # sleep(1.5)
            self.clear_screen()
            while True:
                command = input("Command:")
                command = command.lower()
                self.clear_screen()
                if command == "sync" or command == "s":
                    print("Syncing...")
                    self.client.sync_files()
                if command == "ls" or command == "lf" or command == "local files":
                    print("Local files:")
                    self.print_local_files()
                if command == "rf" or command == "remote files":
                    print("Remote files:")
                    self.print_remote_files()
                if command == "gf" or command == "get file":
                    print("getting file...")
                    print("(not implemented)")
                if command == "diff" or command == "d":
                    self.print_diff_to_server()
                if command == 'exit' or command == 'e':
                    self.client.close_client()
                    self.clear_screen(print_logo=False)
                    break
                else:
                    print(self.get_help())

        except KeyboardInterrupt:
            self.clear_screen(print_logo=False)
            self.client.close_client()


    def print_list(self, list_to_print):
        for element in list_to_print:
            print("\t", element)


    def print_remote_files(self):
        enc_remote_file_list = self.client.servercoms.get_file_list()
        if len(enc_remote_file_list) == 0:
            print("\t(no files on server)")
        else:
            dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
            self.print_list(dec_remote_file_list)


    def print_local_files(self):
        local_file_list = self.client.get_local_file_list()
        if len(local_file_list) == 0:
            print("\t(no files locally)")
        else:
            self.print_list(local_file_list)

    def print_diff_to_server(self):
        local_file_list = self.client.get_local_file_list()
        enc_remote_file_list = self.client.servercoms.get_file_list()
        dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x) for x in dec_remote_file_list]
        files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list)
        files_not_on_client = globals.get_list_difference(pathlib_remote_file_list, local_file_list)
        print("Difference:")
        if len(files_not_on_client) == 0:
            print("\tClient up to date")
        else:
            print("Files not on client:")
            self.print_list(files_not_on_client)
        if len(files_not_on_server) == 0:
            print("\tServer up to date")
        else:
            print("Files not on server:")
            self.print_list(files_not_on_server)

    def clear_screen(self, print_logo=True):
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
        if print_logo:
            figlet = Figlet()
            print(figlet.renderText(globals.PROJECT_NAME))

    def get_help(self):
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
