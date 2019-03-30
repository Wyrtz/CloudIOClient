import os
from enum import Enum

def get_ClaudIOClient_path():
    curdir = os.getcwd()
    proj_name_idx = curdir.find(PROJECT_NAME)
    if proj_name_idx == -1:
        print(curdir)
        raise IndexError
    clIOclpath = curdir[:proj_name_idx] + PROJECT_NAME
    return clIOclpath


def create_folders():
    if not os.path.exists(TEMPORARY_FOLDER):
        os.makedirs(TEMPORARY_FOLDER)
    if not os.path.exists(FILE_FOLDER):
        os.makedirs(FILE_FOLDER)

PROJECT_NAME = "CloudIOClient"
PROJECT_NAME = PROJECT_NAME
WORK_DIR = get_ClaudIOClient_path()
TEST_FOLDER = os.path.join(WORK_DIR, "tests")
TEST_FILE_FOLDER = os.path.join(WORK_DIR, "files_for_testing")
FILE_FOLDER = os.path.join(WORK_DIR, "files")
TEMPORARY_FOLDER = os.path.join(WORK_DIR, "tmp")
create_folders()
DOWNLOADED_FILE_QUEUE = []  # TODO: Make thread safe

def clear_tmp():
    for file in os.listdir(TEMPORARY_FOLDER):
        file_path = os.path.join(TEMPORARY_FOLDER, file)
        os.unlink(file_path)
