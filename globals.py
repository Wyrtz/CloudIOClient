import os
from enum import Enum

PROJECT_NAME = "ClaudIOClient"

def get_ClaudIOClient_path():
    curdir = os.getcwd()
    proj_name_idx = curdir.find(PROJECT_NAME)
    if proj_name_idx == -1:
        print(curdir)
        raise IndexError
    clIOclpath = curdir[:proj_name_idx] + PROJECT_NAME
    return clIOclpath


class globals():
    PROJECT_NAME = "ClaudIOClient"
    WORK_DIR = get_ClaudIOClient_path()
    TEST_FOLDER = os.path.join(WORK_DIR, "tests")
    TEST_FILE_FOLDER = os.path.join(WORK_DIR, "files_for_testing")
    FILE_FOLDER = os.path.join(WORK_DIR, "files")
    TEMPORARY_FOLDER = os.path.join(WORK_DIR, "tmp")

