import os
import platform
import secrets
from getpass import getpass
from time import sleep

from pyfiglet import Figlet
from colorama import Fore
from colorama import Back
from colorama import Style
import colorama

from resources import globals
import pathlib as pl

from client import Client
import client
from security import keyderivation
from security.keyderivation import BadKeyException, BadPasswordSelected
from security.secretsharing import FInt


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
            init_cmd = input("Want to [login] or [replace_password_using_shares]?")
            if init_cmd != 'login' and init_cmd != 'replace_password_using_shares':
                print("Sorry, I did not understand this.")
                return
            elif init_cmd == 'replace_password_using_shares' or init_cmd == "rpus":
                self.replace_pw_using_shares()
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
                sleep(1)
                self.start_user_interface()
                return
            self.clear_screen(False)
            welcome = "Welcome   " + username + " !"
            print(figlet.renderText(welcome))
            sleep(1.5)
            self.clear_screen()
            self.get_or_delete_avaliable = False

            self.start_user_input_loop()

        except KeyboardInterrupt:
            self.clear_screen(print_logo=False)
            self.client.close_observers()

    def start_user_input_loop(self):
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

                if command == 'df' or command == "del" or command == 'delete_file':
                    success = self.interact_with_server(commands, 'df')
                    if not success:
                        continue

            self.get_or_delete_avaliable = False
            if command == "sync" or command == "s":
                print("Synchronising...")
                sync_dict = self.generate_sync_dict()
                self.client.sync_files(sync_dict)
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
                self.print_diff_to_server()
            elif command == "ss" or command == "sync_status":
                self.get_or_delete_avaliable = True
                sync_dict = self.generate_sync_dict()
                self.print_sync_dict(sync_dict)
            elif command == "csf" or command == "create_shared_folder":
                folder_name = input("Name of shared folder:\n") # ToDo: check if legal folder name
                relative_folder_path = pl.Path.joinpath(globals.FILE_FOLDER, folder_name)
                if relative_folder_path.exists():
                    print("Folder already exists!")
                    continue
                key = self.generate_key_for_folder_shareing(relative_folder_path)
                secret = self.client.create_shared_folder(relative_folder_path, key)
                print(secret[0])

            elif command == "asf" or command == "add_shared_folder":
                self.add_shared_folder()
            elif command == 'exit' or command == 'e':
                raise KeyboardInterrupt
            elif command == 'replace_password' or command == "re_pw":
                self.replace_password()
            elif command == 'backup_password':
                self.backup_password()
            print()
            print(self.divider)
            print(self.get_help())

    def replace_password(self):
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
            requested_file = globals.SERVER_FILE_LIST[number - 1][0]
        except IndexError:
            print(error_message)
            return False

        if command == "gf" or command == "get":
            print("Getting file...")
            self.client.get_file(requested_file)   # ToDO: can run "get file" on files we already have, and requests for files the server does not have is wierd!
            return True

        if command == 'df' or command == "del":
            if pl.Path.exists(requested_file):
                answer = input("Delete local file as well ? (y,n)")
                answer = answer.lower()
                if answer == "y" or answer == "yes":
                    pl.Path.unlink(requested_file)
                    return True
            print("Deleting file...")
            print(requested_file)
            self.client.delete_remote_file(requested_file)  # ToDO: not done! If file is on server, not on client, fucks up (what file to ask for del ?)
            return True

    def replace_pw_using_shares(self):
        shares_input = self.get_shares_from_user()
        has_new_pw = False
        while not has_new_pw:
            username = input("Select a username. (Can pick new or the same)")
            new_pw = getpass("Input new password.")
            new_pw_ = getpass("Repeat new password.")
            if new_pw == new_pw_:
                try:
                    client.replace_key_from_backup(shares_input, username, new_pw)
                except BadKeyException:
                    print("Failed to recover from the shares. Did you input them right? Exiting...")
                    sleep(1)
                    return
                except BadPasswordSelected:
                    print("Invalid password selected. Try another one.")
                    continue
                #  No exception. Password has been replaced with new.
                return
            else:
                print("Passwords didn't match. Try again.")

    def get_shares_from_user(self) -> list:
        shares_input = []
        amount_needed = -1
        while len(shares_input) != amount_needed:
            if amount_needed != -1:
                print("Expecting " + str(amount_needed - len(shares_input)) + " more shares.")
            x = input("Input the first value of a share. (or 'exit' to exit)\n")
            if x == 'exit':
                raise KeyboardInterrupt
            y = input("Input the second value of THE SAME share. (or 'exit' to exit)\n")
            if y == 'exit':
                raise KeyboardInterrupt
            t = input("Input the third value of THE SAME share. (or 'exit' to exit)\n")
            if t == 'exit':
                raise KeyboardInterrupt
            try:
                x = int(x)
                y = FInt(int(y))
                t = int(t)
            except ValueError:
                print("Could not interpret the share as a share. Try inputting it again:")
                continue
            if amount_needed == -1:
                amount_needed = t + 1
            elif t + 1 != amount_needed:
                print("The share input does not match the other shares. Try inputting again:")
                continue
            if shares_input.__contains__([x, y, t]):
                continue
            else:
                shares_input = shares_input + [[x, y, t]]

        return shares_input


    def print_remote_files(self):
        enc_remote_file_list = self.client.servercoms.get_file_list()
        if len(enc_remote_file_list) == 0:
            print("\t(no files on server)")
        else:
            globals.SERVER_FILE_LIST = self.client.file_crypt.decrypt_file_list(enc_remote_file_list)
            file_names_only = [touble[0] for touble in globals.SERVER_FILE_LIST]
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
        globals.SERVER_FILE_LIST = self.dec_remote_file_list
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

    def print_list(self, list_names_to_print):
        """Prints a given list, with each line enumerated"""
        # list_to_print_str = [str(x) for x in list_names_to_print]
        # longest_element_length = len(max(list_to_print_str, key=len))
        print(f"{Back.BLACK}\t #{self.calculate_spacing(1)}File Name")
        for numb, element in enumerate(list_names_to_print):
            print("\t", numb + 1, end=self.calculate_spacing(numb))
            print(element)

    def generate_key_for_folder_shareing(self, relative_folder_path):
        pw = secrets.token_bytes(32)  # 32 bytes long password
        kd = keyderivation.KeyDerivation(str(relative_folder_path))
        key = kd.derive_key(pw, False)
        return key

    def add_shared_folder(self):
        shares = self.get_shares_from_user()
        self.client.add_key_from_shares(shares)

    def backup_password(self):
        r1 = input("You are about to backup your password. Are you sure you want to do this?(y/n)")
        if r1 == 'n':
            return
        elif r1 != 'y':
            print('Sorry, I could not interpret that input.')
            return
        total = input("How many pieces do you want in total?(int)")
        try:
            total = int(total)
        except ValueError:
            print("Sorry, can't interpret that as an int. Exiting backup.")
            return
        if total < 1:
            print("That's not a valid amount of total shares. Should be > 0. Exiting backup.")
            return
        to_recover_from = input("How many pieces should be necessary to recover?(int)")
        try:
            to_recover_from = int(to_recover_from)
        except ValueError:
            print("Sorry, can't interpret that as an int. Exiting backup.")
            return
        if to_recover_from < 1 or to_recover_from > total:
            print("That's not a valid amount of shares to recover from.")
            print("Should be > 0 and < total amount of shares. Exiting backup.")
            return
        password = getpass("Type in your password to confirm.")
        shares = self.client.backup_key(password, to_recover_from, total)
        print("These are your shares:")
        for share in shares:
            print(share)
        print("When you have written these down or distributed them press enter.")
        input('Remember; these should only be given to parties you can trust not to collaborate against you.')

    def generate_sync_dict(self):
        """Generates a dictionary with key:files value:(client_time, server_time)
        representing the time stamp of a file for client or server. time stamp 0 = this party does not have the file"""
        # Create a dictionary with key = file name, value = timestamp for local files
        local_file_list = self.client.get_local_file_list()
        c_dict = {}
        for element in local_file_list:
            c_dict[element] = element.stat().st_mtime

        # Do the same for server files:
        enc_remote_file_list = self.client.servercoms.get_file_list()
        dec_remote_file_list = self.client.file_crypt.decrypt_file_list_extended(enc_remote_file_list)
        globals.SERVER_FILE_LIST = dec_remote_file_list
        pathlib_remote_file_list = [(pl.Path(x[0]), x[3]) for x in dec_remote_file_list]  # idx 0 = name, idx 3 = timestamp
        s_dict = {}
        for element in pathlib_remote_file_list:
            s_dict[element[0]] = element[1]

        # Copy the client dict, and add the uniques from the server dict.
        # Value = 0 since this means the client does not have this file, thus setting a timestamp of as old as possible
        full_dict = c_dict.copy()
        for key in s_dict:
            if key not in full_dict:
                full_dict[key] = 0

        # Create the tuple dictionary key = filename, value = (c_time, s_time)
        for key in full_dict:
            val = s_dict.get(key) if key in s_dict else 0
            full_dict[key] = (full_dict.get(key), val)

        return full_dict

    def print_sync_dict(self, sync_dict: dict):
        """Prints a synchronisation dictionary as produced by "generate_sync_dict"""
        i = 0
        print(f"{Back.BLACK}\t #{self.calculate_spacing(1)}File Name")
        if len(sync_dict) == 0:
            print("\tNo files on server or client")
        for key in sync_dict:
            print("\t", i + 1, end=self.calculate_spacing(i))
            c_time, s_time = sync_dict.get(key)
            colour = Back.GREEN
            if c_time > s_time:
                colour = Back.BLUE
            elif c_time < s_time:
                colour = Back.RED
            print(f'{colour}{key}')
            i += 1

        print(self.divider)
        print(f"{Back.GREEN}\tGreen:\tUp to date")
        print(f"{Back.BLUE}\tBlue:\tClient version newer than server version")
        print(f"{Back.RED}\tRed:\tServer version newer than client version")
        print(self.divider)

    def clear_screen(self, print_logo=True):
        """Clears the terminal no matter the OS"""
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
        if print_logo:
            figlet = Figlet()
            print(f'{Fore.CYAN}{figlet.renderText(globals.PROJECT_NAME)}{Style.RESET_ALL}')

    def calculate_spacing(self, numb):
        len_numb = len(str(numb + 1))
        return " " * (6 - len_numb)

    def get_help(self):
        """Prints the avaliable options in this software"""
        help = f"""
Available commands:
{Fore.GREEN}    What                Command {Style.RESET_ALL}
    _____________________________
    Help                (h, help)
    Sync                (s, sync)
    Local_files         (ls, lf, local_files)
    Remote_files        (rf, remote_files)
    Diff_local/remote   (diff, d)
    Sync status         (ss, sync_status)
    Replace password    (re_pw, replace_password)
    Create shared folder(csf, create_shared_folder)
    Add shared folder   (asf, add_shared_folder)
    Backup password us- (backup_password)
        ing shares.
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
