import os
import platform
from getpass import getpass
from time import sleep

from pyfiglet import Figlet
from colorama import Fore
from colorama import Back
from colorama import Style
import colorama

from resources import globals
import pathlib as pl
import datetime

from client import Client
from security import keyderivation
from security.keyderivation import BadKeyException, BadPasswordSelected


class CLI:

    def __init__(self):
        colorama.init(autoreset=True)
        self.divider = "*"*40
        self.start_user_interface()

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
                print(f"{Fore.RED}Wrong username or password")
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
                elif command == "ls" or command == "lf" or command == "local_files":
                    print("Local files:")
                    self.print_local_files()
                elif command == "rf" or command == "remote_files":
                    self.get_or_delete_avaliable = True
                    print("Remote files:")
                    self.print_remote_files()
                elif command == "diff" or command == "d":
                    self.get_or_delete_avaliable = True
                    # self.print_diff_to_server()
                    self.print_sync_status()
                elif command == 'exit' or command == 'e':
                    raise KeyboardInterrupt
                elif command == 'replace_password' or command == "re_pw":
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
                    print(self.divider)
                    print(self.get_help())

        except KeyboardInterrupt:
            self.clear_screen(print_logo=False)
            self.client.close_observers()

    def interact_with_server(self, commands, command):
        error_message = f"{Fore.RED}Provide what file (number) you want"
        if not len(commands) == 2:
            print(f'{Fore.RED}ERROR, 2 arguments required (command, number)')
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

        if command == "gf" or command == "get":
            print("Getting file...")
            self.client.get_file(requested_file)
            return True

        if command == 'df' or command == "del":
            print("Deleting file...")
            print(requested_file)
            self.client.delete_remote_file(requested_file)

    def calculate_spaceing(self, numb):
        len_numb = len(str(numb+1))
        return " "*(6-len_numb)

    def print_list(self, list_names_to_print, list_times_to_print=None):
        # list_to_print_str = [str(x) for x in list_names_to_print]
        # longest_element_length = len(max(list_to_print_str, key=len))
        print(f"{Back.BLACK}\t #{self.calculate_spaceing(1)}File Name")
        for numb, element in enumerate(list_names_to_print):
            print("\t", numb+1, end=self.calculate_spaceing(numb))
            if list_times_to_print:
                try:
                    s_time = list_times_to_print[numb]
                except IndexError:
                    s_time = 0
                try:
                    c_time = element.stat().st_mtime
                except FileNotFoundError:
                    c_time = 0
                colour = Back.GREEN
                if c_time > s_time:
                    colour = Back.BLUE
                elif c_time < s_time:
                    colour = Back.RED
                print(f'{colour}{element}')
                continue
            print(element) #, datetime.datetime.fromtimestamp(pl.Path(element).stat().st_mtime), sep="\t")

        print(self.divider)
        print(f"{Back.GREEN}\tGreen:\tUp to date")
        print(f"{Back.BLUE}\tBlue:\tClient version newer than server version")
        print(f"{Back.RED}\tRed:\tServer version newer than client version")
        print(self.divider)

    def print_remote_files(self):
        enc_remote_file_list = self.client.servercoms.get_file_list()
        if len(enc_remote_file_list) == 0:
            print("\t(no files on server)")
        else:
            self.dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
            file_names_only = [touble[0] for touble in self.dec_remote_file_list]
            self.print_list(file_names_only)

    def print_local_files(self):
        self.local_file_list = self.client.get_local_file_list()
        if len(self.local_file_list) == 0:
            print("\t(no files locally)")
        else:
            self.print_list(self.local_file_list)

    def print_diff_to_server(self):
        local_file_list = self.client.get_local_file_list()
        enc_remote_file_list = self.client.servercoms.get_file_list()
        self.dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x[0]) for x in self.dec_remote_file_list]
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

    def print_sync_status(self):
        local_file_list = self.client.get_local_file_list()
        enc_remote_file_list = self.client.servercoms.get_file_list()
        dec_remote_file_list = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
        pathlib_remote_file_list = [pl.Path(x[0]) for x in dec_remote_file_list]
        files_not_on_server = globals.get_list_difference(local_file_list, pathlib_remote_file_list )
        l = [x[0] for x in dec_remote_file_list]
        l.extend([pl.Path(x) for x in files_not_on_server])
        self.print_list(l, [x[1] for x in dec_remote_file_list])



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
    Get_file            (gf #, get #, get_file #)    
    Delete_file         (df #, del #, delete_file #)
        
        """
        if self.get_or_delete_avaliable:
            help += additional
        return help

if __name__ == "__main__":
    # serverIP = 'wyrnas.myqnapcloud.com:8000'
    cli = CLI()
