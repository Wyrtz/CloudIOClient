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

from client import Client
import client
from security import keyderivation
from security.keyderivation import BadKeyException, BadPasswordSelected
from security.secretsharing import FFInt


class CLI:
    """Class for a CLI user interface for the CloudIOclient"""

    def __init__(self):
        colorama.init(autoreset=True)
        self.divider = "*" * 40
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
        """Runs after a user is logged in to show and perform various file actions"""
        while True:
            command_input = input("Command:")
            commands = command_input.split(" ")
            command = commands[0]
            command = command.lower()
            self.clear_screen()
            if self.get_or_delete_avaliable:
                if command == "gf" or command == "get_file":
                    try:
                        idx = int(commands[1])
                    except ValueError:
                        print("Could not interpret second entry as a number.")
                        continue
                    except IndexError:
                        print("To use this command (gf) provide a number as part of the command.")
                        continue
                    try:
                        file_rel_path = self.name_list[idx - 1]  # One-indexing -> zero-indexing
                    except IndexError:
                        print("The inputted number is invalid.")
                        continue
                    success = self.interact_with_server('gf', file_rel_path)
                    if not success:
                        continue

                if command == 'df' or command == "del" or command == 'delete_file':
                    try:
                        idx = int(commands[1])
                    except ValueError:
                        print("Could not interpret second entry as a number.")
                        continue
                    except IndexError:
                        print("To use this command (gf) provide a number as part of the command.")
                        continue
                    try:
                        file_rel_path = self.name_list[idx - 1]  # One-indexing -> zero-indexing
                    except IndexError:
                        print("The inputted number is invalid.")
                        continue
                    success = self.interact_with_server('df', file_rel_path)
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
                self.name_list = self.print_diff_to_server()
            elif command == "ss" or command == "sync_status":
                self.get_or_delete_avaliable = True
                sync_dict = self.client.generate_sync_dict()
                self.name_list = list(sync_dict)
                self.print_sync_dict(sync_dict)
            elif command == "csf" or command == "create_shared_folder":
                folder_name = input("Name of shared folder:\n")
                if not globals.is_safe_folder_name(folder_name):
                    print("Illegal pathname.")
                    continue
                absolute_folder_path = pl.Path.joinpath(globals.FILE_FOLDER, folder_name)
                if absolute_folder_path.exists():
                    print("Folder already exists!")
                    continue
                key = globals.generate_random_key()
                self.client.create_shared_folder(pl.Path(folder_name), key)
                print("Give this key to whoever you want to share the folder with. Send it safely!")
                print(key.hex())

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
        """Method for replacing the users password"""
        self.clear_screen()
        print("Initiated password replacement.")
        old_pw = getpass("Type old password:")
        new_password = getpass("Type new password:")
        new_password_ = getpass("Repeat new password:")
        if new_password != new_password_:
            self.clear_screen()
            print("New password doens't match.")
        else:
            try:
                print("Replacing password. Might take a second!")
                self.client.replace_password(old_pw=old_pw, new_pw=new_password)
                input("Replaced password successfully. Press enter to continue.")
                self.clear_screen()
            except (BadKeyException, BadPasswordSelected):
                input("Failed to replace password. Press enter to continue.")
                self.clear_screen()

    def interact_with_server(self, command: str, file_rel_path: pl.Path):
        """Interpreting user commands related to manipulating listed files

        Args:
            command: input from the user on string form
            file_rel_path: the file in question to either get or delete
        """
        error_message = f"{Fore.RED}Provide what file (number) you want"  # TODO: Remove? idx out of bound ??
        exists_remotely = file_rel_path in list(globals.SERVER_FILE_DICT)
        exists_locally = pl.Path.exists(file_rel_path)

        if command == "gf" or command == "get":
            if not exists_remotely:
                print("File doesn't exist remotely.")
                return True
            print("Getting file...")
            self.client.get_file(file_rel_path)
            return True

        if command == 'df' or command == "del":
            if exists_locally:
                answer = input("Delete local file? (y,n)")
                answer = answer.lower()
                if answer == "y" or answer == "yes":
                    pl.Path.unlink(file_rel_path)
            if exists_remotely:
                print("Deleting file on server...")
                print(file_rel_path.as_posix())
                self.client.delete_remote_file(file_rel_path)
            return True

    def replace_pw_using_shares(self):
        """Replace username and password from shares"""
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
        """Run the loop of acquiring shares for Shamirs Secret Sharing Scheme from the user

        Returns:
            list: list of lists, with each sublist containing a shares x,y coordinate and the # of secrets you can
            have without restoring the secret
        """
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
                y = FFInt(int(y))
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
        """Get the remote file list as per globals give it to print_list for printing"""
        enc_remote_file_list = self.client.servercoms.get_file_list()
        if len(enc_remote_file_list) == 0:
            print("\t(no files on server)")
        else:
            file_names_only = list(globals.SERVER_FILE_DICT)
            self.print_list(file_names_only)

    def print_local_files(self):
        """Get the local file list and give it to print_list for printing"""
        self.local_file_list = self.client.get_local_file_list()
        if len(self.local_file_list) == 0:
            print("\t(no files locally)")
        else:
            self.print_list(self.local_file_list)

    def print_diff_to_server(self) -> list:
        """
        Get local and remote file list and print the unique files from each list

        Returns:
            list: a list containing the file names which are unique to either remote or local files
        """
        local_file_list = self.client.get_local_file_list()
        self.client.update_server_file_list()
        remote_file_names = list(globals.SERVER_FILE_DICT)
        files_not_on_server = globals.get_list_difference(local_file_list, remote_file_names)
        files_not_on_client = globals.get_list_difference(remote_file_names, local_file_list)
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
            self.print_list(files_not_on_server, len(files_not_on_client))
        return files_not_on_client + files_not_on_server

    def print_list(self, list_names_to_print, offset=0):
        """Prints a given list, with each line enumerated

        Args:
            list_names_to_print: a list of the files to print
            offset: the tab-space offset to be used (default= 0)
        """
        print(f"{Back.BLACK}\t #{self.calculate_spacing(1)}File Name")
        for numb, element in enumerate(list_names_to_print):
            print("\t", numb + 1 + offset, end=self.calculate_spacing(numb))
            print(element)

    def add_shared_folder(self):
        """Ask the user for a key on hex format to add it to the client"""
        hex_key = input("Input key:\n")
        try:
            key = bytes.fromhex(hex_key)
        except ValueError:
            print("Invalid key!")
            return
        self.client.add_share_key(key)

    def backup_password(self):
        """Run user input loop for creating Shamir Secret Sharing Scheme for the password"""
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
        if len(shares) == 0:
            print("No shares were produced.")
            return
        print("These are your shares:")
        for share in shares:
            print(share)
        print("When you have written these down or distributed them press enter.")
        input('Remember; these should only be given to parties you can trust not to collaborate against you.')
        self.clear_screen()

    def print_sync_dict(self, sync_dict: dict):
        """Prints a synchronisation dictionary as produced by "generate_sync_dict

        Args:
            sync_dict: a dictionary of all the files to be printed and their assosiated data (see create_sync_dict)
        """
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

    def clear_screen(self, print_logo: bool=True):
        """Clears the terminal no matter the OS

        Args:
            print_logo: whether or not the logo should be printed after the screen is cleared
        """
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
    cli = CLI()
