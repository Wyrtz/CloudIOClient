import os
import pathlib as pl

def get_CloudIOClient_path():
    curdir = pl.Path.cwd()
    idx = curdir.parts.index(PROJECT_NAME)
    return curdir.parents[len(curdir.parts)-idx-2]

def create_folders():
    if not os.path.isdir(TEMPORARY_FOLDER):
        os.mkdir(TEMPORARY_FOLDER)
    if not os.path.isdir(FILE_FOLDER):
        os.mkdir(FILE_FOLDER)

PROJECT_NAME = "CloudIOClient"
PROJECT_NAME = PROJECT_NAME
WORK_DIR = get_CloudIOClient_path()
TEST_FOLDER = pl.PurePath.joinpath(WORK_DIR, "tests")
TEST_FILE_FOLDER = pl.PurePath.joinpath(WORK_DIR, "files_for_testing")
FILE_FOLDER = pl.PurePath.joinpath(WORK_DIR, "files")
TEMPORARY_FOLDER = pl.PurePath.joinpath(WORK_DIR, "tmp")
create_folders()
DOWNLOADED_FILE_QUEUE = []

def clear_tmp():
    for file in os.listdir(TEMPORARY_FOLDER):
        file_path = os.path.join(TEMPORARY_FOLDER, file)
        os.unlink(file_path)
