import os
import pathlib as pl
import secrets
import string
from asyncio import sleep
from typing import Dict


def get_CloudIOClient_path() -> pl.Path:
    """Extract the path of cloudIOclient for relative pathing. Relative paths are typically from here."""
    curdir = pl.Path.cwd()
    if curdir.name == PROJECT_NAME:
        return curdir
    idx = 0
    while curdir.parents[idx].name != PROJECT_NAME:
        idx += 1
    return curdir.parents[idx]


def create_file_folders():
    """Create the folders if they do not already exists"""
    if not os.path.isdir(TEMPORARY_FOLDER):
        os.mkdir(TEMPORARY_FOLDER)
    if not os.path.isdir(FILE_FOLDER):
        os.mkdir(FILE_FOLDER)


def clear_tmp():
    """Clear all files in the tmp folder, which is used to encrypt/ decrypt files"""
    for file in os.listdir(TEMPORARY_FOLDER):
        file_path = os.path.join(TEMPORARY_FOLDER, file)
        try:
            os.unlink(file_path)
        except PermissionError:
            sleep(0.1)
            clear_tmp()


def get_list_difference(list_1: list, list_2: list) -> list:  # TODO: What if name duplication? What?
    """
    Returns the unique elements of list 1 compared to list 2

    Args:
        list_1 (list): list of elements
        list_2 (list): list of elements

    """
    return [x for x in list_1 if x not in list_2]


def generate_random_nonce(length: int = 12):
    """Generate a cryptographicly secure nonce

    Args:
        length (int): number of random bytes to return
    """
    return secrets.token_bytes(length)


def generate_random_key() -> bytes:
    """Generate a random username and password to generate a """
    # user = secrets.token_bytes(10)
    # pw = secrets.token_bytes(32)  # 32 bytes long password
    # kd = keyderivation.KeyDerivation(str(user))
    # key = kd.derive_key(pw, False)
    key = secrets.token_bytes(32)
    return key


class FileInfo:
    """Encapsulates the elements of a file"""

    def __init__(self, rel_file_path: pl.Path, file_name_nonce: bytes, enc_path: str, time_stamp: float):
        """
        Args:
            rel_file_path: the relative path of the file, relative to the project folder
            file_name_nonce: the nonce the filename has been encrypted under
            enc_path  : the encrypted file name
            time_stamp: the modify time of the file
        """
        self.path = rel_file_path
        self.nonce = file_name_nonce
        self.enc_path = enc_path
        self.time_stamp = time_stamp

    def __str__(self) -> str:
        return self.path.as_posix() + "->" + self.enc_path

    def __repr__(self) -> str:
        return self.__str__()


def is_safe_folder_name(folder_name: str) -> bool:
    """
    Checks a string if it is a legal filename

    Args:
        folder_name: the string to be checked if string is valid folder name

    Returns:
        bool: True if valid folder name, False otherwise

    """
    legal_chars = string.ascii_letters + '-_ ' + string.digits
    if not all([char in legal_chars for char in folder_name]):
        return False
    return True


PROJECT_NAME = "CloudIOClient"
PROJECT_NAME = PROJECT_NAME
WORK_DIR = get_CloudIOClient_path()
RESOURCE_DIR = pl.Path.joinpath(WORK_DIR, 'resources')
TEST_FOLDER = pl.Path.joinpath(WORK_DIR, "tests")
TEST_FILE_FOLDER = pl.Path.joinpath(WORK_DIR, "files_for_testing")
FILE_FOLDER = pl.Path.joinpath(WORK_DIR, "files")
TEMPORARY_FOLDER = pl.Path.joinpath(WORK_DIR, "tmp")
create_file_folders()
DOWNLOADED_FILE_QUEUE = []
SERVER_LOCATION = 'wyrnas.myqnapcloud.com:8001'
KEY_HASHES = pl.Path.joinpath(RESOURCE_DIR, 'key_hashes.txt')
ENC_OLD_KEYS = pl.Path.joinpath(RESOURCE_DIR, 'enc_keys.txt')  # Should contain old key encryptions
SHARED_KEYS = RESOURCE_DIR / "shared_keys"
SERVER_FILE_DICT: Dict[pl.Path, FileInfo] = {}
