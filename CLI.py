import os
import platform
from getpass import getpass
from time import sleep

from pyfiglet import Figlet
from colorama import Fore
from colorama import Style
import colorama

from resources import globals
import pathlib as pl

from client import Client
from security import keyderivation
from security.keyderivation import BadKeyException, BadPasswordSelected


class CLI:

    def __init__(self):
        self.start_user_interface()
        colorama.init()

    def start_user_interface(self):
        """While loop that reads input and calls associated functions"""
        figlet = Figlet()
        try:
            self.clear_screen()
            is_testing = None
            while is_testing is None:
                bool_input = input("Are we testing locally? (y/n):")
                if bool_input == "y":
                    is_testing = True
                elif bool_input == "n":
                    is_testing = False
                else:
                    self.clear_screen()
                    input("Could not interpret input. Let's try again:")
            if is_testing:
                server_location = "127.0.0.1:443"
            else:
                server_location = globals.SERVER_LOCATION
            if pl.Path(globals.KEY_HASHES).exists():
                username = input("Username:")
                password = getpass("Password:")
            while not pl.Path(globals.KEY_HASHES).exists():
                username = input("Select new username:")
                password = getpass("Select new password (length > 12):")
                password_ = getpass("Confirm new password (length > 12):")
                if password != password_:
                    self.clear_screen()
                    input("Password didn't match. Press enter to try again.")
                    continue
                else:
                    try:
                        keyderivation.KeyDerivation(username).select_first_pw(password)
                    except BadPasswordSelected:
                        self.clear_screen()
                        input("Password not acceptable. Press enter to try again.")
                        continue
            if not pl.Path(globals.KEY_HASHES).exists():
                keyderivation.KeyDerivation(username).select_first_pw(password)
            self.clear_screen()
            try:
                self.client = Client(username, password, server_location=server_location)
            except BadKeyException:
                self.clear_screen()
                print(f"{Fore.RED}Wrong username or password{Style.RESET_ALL}")
                sleep(2)
                self.start_user_interface()
            self.clear_screen(False)
            welcome = "Welcome   " + username + " !"
            print(figlet.renderText(welcome))
            sleep(1.5)
            self.clear_screen()
            self.get_or_delete_avaliable = False
            while True:
                command_input = input("Command:")
                commands = command_input.split(" ")
                command = commands[0]
                command = command.lower()
                self.clear_screen()
                if self.get_or_delete_avaliable:
                    if command == "gf" or command == "get_file":
                        success = self.interact_with_server(commands, 'gf')
                        if not success:
                            continue

                    if command == 'df' or command == 'delete_file':
                        success = self.interact_with_server(commands, 'df')
                        if not success:
                            continue

                self.get_or_delete_avaliable = False
                if command == "sync" or command == "s":
                    print("Synchronising...")
                    self.client.sync_files()
                    print("Synchronising done!")
                if command == "ls" or command == "lf" or command == "local_files":
                    print("Local files:")
                    self.print_local_files()
                if command == "rf" or command == "remote_files":
                    self.get_or_delete_avaliable = True
                    print("Remote files:")
                    self.print_remote_files()
                if command == "diff" or command == "d":
                    self.get_or_delete_avaliable = True
                    self.print_diff_to_server()
                if command == 'exit' or command == 'e':
                    raise KeyboardInterrupt
                if command == 'replace_password' or command == "re_pw":
                    self.clear_screen()
                    print("Initiated password replacement.")
                    old_pw = getpass("Type old password:")
                    new_password = getpass("Type new password:")
                    new_password_ = getpass("Repeat new password:")
                    if new_password != new_password_:
                        self.clear_screen()
                        print("New password doens't match.")
                    try:
                        self.client.kd.replace_pw(old_pw=old_pw, new_pw=new_password)
                        input("Replaced password successfully. Press enter to continue.")
                        self.clear_screen()
                    except (BadKeyException, BadPasswordSelected):
                        input("Failed to replace password. Press enter to continue.")
                        self.clear_screen()
                else:
                    print()
                    print("*"*40)
                    print(self.get_help())

        except KeyboardInterrupt:
            self.clear_screen(print_logo=False)
            self.client.close_client()

    def interact_with_server(self, commands, command):
        error_message = f"{Fore.RED}Provide what file (number) you want{Style.RESET_ALL}"
        if not len(commands) == 2:
            print(f'{Fore.RED}ERROR, 2 arguments required (command, number){Style.RESET_ALL}')
            self.get_or_delete_avaliable = False
            return False
        number = commands[1]
        try:
            number = int(number)
        except ValueError:
            print(error_message)
            return False
        try:
            requested_file = self.dec_remote_file_list[number - 1]
        except IndexError:
            print(error_message)
            return False

        if command == "gf":
            print("Getting file...")
            self.client.get_file(requested_file)
            return True

        if command == 'df':
            print("Deleting file...")
            print(requested_file)
            self.client.delete_remote_file(requested_file)

    def print_list(self, list_to_print):
        list_to_print_str = [str(x) for x in list_to_print]
        # longest_element_length = len(max(list_to_print_str, key=len))
        spaceing = lambda fewer_spacees: " " * (6-fewer_spacees)
        print(f"{Fore.GREEN}\t #{spaceing(1)}File Name{Style.RESET_ALL}")
        for numb, element in enumerate(list_to_print):
            len_numb = len(str(numb))
            print("\t", numb+1, end=spaceing(len_numb))
            print(element)

    def print_remote_files(self):
        enc_remote_file_list = self.client.servercoms.get_file_list(self.client.userID)
        if len(enc_remote_file_list) == 0:
            print("\t(no files on server)")
        else:
            self.dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
            self.print_list(self.dec_remote_file_list)

    def print_local_files(self):
        self.local_file_list = self.client.get_local_file_list()
        if len(self.local_file_list) == 0:
            print("\t(no files locally)")
        else:
            self.print_list(self.local_file_list)

    def print_diff_to_server(self):
        local_file_list = self.client.get_local_file_list()
        enc_remote_file_list = self.client.servercoms.get_file_list(self.client.userID)
        self.dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x) for x in self.dec_remote_file_list]
        files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list)
        files_not_on_client = globals.get_list_difference(pathlib_remote_file_list, local_file_list)
        print("Difference:")
        print("*** Client misses {} files ***".format(len(files_not_on_client)))
        if len(files_not_on_client) == 0:
            print("\t(Client up to date)")
        else:
            self.print_list(files_not_on_client)
        print("\n*** Server misses {} files ***".format(len(files_not_on_server)))
        if len(files_not_on_server) == 0:
            print("\t(Server up to date)")
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
            print(f'{Fore.CYAN}{figlet.renderText(globals.PROJECT_NAME)}{Style.RESET_ALL}')

    def get_help(self):
        help = f"""
Available commands:
{Fore.GREEN}    What                Command {Style.RESET_ALL}
    _____________________________
    Help                (h, help)
    Sync                (s, sync)
    Local_files         (ls, lf, local_files)
    Remote_files        (rf, remote_files)
    Diff_local/remote   (diff, d)
    Replace password    (replace pw, replace password)
    Exit                (e, exit)
                        """
        additional = """
    Get_file            (gf #, get_file #)    
    Delete_file         (df #, delete_file #)
        
        """
        if self.get_or_delete_avaliable:
            help += additional
        return help

if __name__ == "__main__":
    # serverIP = 'wyrnas.myqnapcloud.com:8000'
    cli = CLI()
