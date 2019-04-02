import os

curr_path = os.getcwd()
TEMPORARY_FOLDER = os.path.join(curr_path, "tmp")
FILE_FOLDER = os.path.join(curr_path, "files")
TESTING = False


def create_folders():
    if not os.path.isdir(TEMPORARY_FOLDER):
        os.mkdir(TEMPORARY_FOLDER)
    if not os.path.isdir(FILE_FOLDER):
        os.mkdir(FILE_FOLDER)


DOWNLOADED_FILE_QUEUE = []  # TODO: Make thread safe

def clear_tmp():
    for file in os.listdir(TEMPORARY_FOLDER):
        file_path = os.path.join(TEMPORARY_FOLDER, file)
        os.unlink(file_path)
