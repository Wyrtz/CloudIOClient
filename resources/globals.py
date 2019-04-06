import os
import pathlib as pl
import secrets
from asyncio import sleep


def get_CloudIOClient_path():
    curdir = pl.Path.cwd()
    if curdir.name == PROJECT_NAME:
        return curdir
    idx = 0
    while curdir.parents[idx].name != PROJECT_NAME:
        idx += 1
    return curdir.parents[idx]

def create_folders():
    if not os.path.isdir(TEMPORARY_FOLDER):
        os.mkdir(TEMPORARY_FOLDER)
    if not os.path.isdir(FILE_FOLDER):
        os.mkdir(FILE_FOLDER)


PROJECT_NAME = "CloudIOClient"
PROJECT_NAME = PROJECT_NAME
WORK_DIR = get_CloudIOClient_path()
RESOURCE_DIR = pl.Path.joinpath(WORK_DIR, 'resources')
TEST_FOLDER = pl.Path.joinpath(WORK_DIR, "tests")
TEST_FILE_FOLDER = pl.Path.joinpath(WORK_DIR, "files_for_testing")
FILE_FOLDER = pl.Path.joinpath(WORK_DIR, "files")
TEMPORARY_FOLDER = pl.Path.joinpath(WORK_DIR, "tmp")
create_folders()
DOWNLOADED_FILE_QUEUE = []
SERVER_LOCATION = 'wyrnas.myqnapcloud.com:8000'
KEY_HASHES = pl.Path.joinpath(RESOURCE_DIR, 'key_hashes.txt')
KEY_SALTS = pl.Path.joinpath(RESOURCE_DIR, 'key_salts.txt')  # TODO: Perhaps instead of static make random & record all salts.
ENC_OLD_KEYS = pl.Path.joinpath(RESOURCE_DIR, 'enc_keys.txt')  # Should contain old key encryptions


def clear_tmp():
    for file in os.listdir(TEMPORARY_FOLDER):
        file_path = os.path.join(TEMPORARY_FOLDER, file)
        try:
            os.unlink(file_path)
        except PermissionError:
            sleep(0.1)
            clear_tmp()


def get_nonce(length=12):
    return secrets.token_bytes(length)
