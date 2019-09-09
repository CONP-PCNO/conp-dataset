from os import listdir, walk
from os.path import isdir, exists, join, abspath, basename, dirname
from random import random
import datalad.api as api


def recurse(directory, odds):
    """
    recurse recursively checks each file in directory and sub-directories with odds chance.
    Odds is a positive decimal that dictates how likely a file is to be tested from 0 (no chance) to 1 or
    above (100% chance). This function tests for if files can be retrieved with datalad and if they can't,
    if there is an authentication setup for security.
    """

    # Get all file names in directory
    files = listdir(directory)

    # Loop through every file
    for file_name in files:

        # If the file name is .git or .datalad, ignore
        if file_name == ".git" or file_name == ".datalad":
            continue

        full_path = join(directory, file_name)

        # If the file is a directory
        if isdir(full_path):

            return recurse(full_path, odds)

        # If the file is a broken symlink and with odd chance
        elif not exists(full_path) and random() < odds:
            msg = api.get(path=full_path, on_failure="ignore", return_type="item-or-list")

            # Check for authentication
            if msg["status"] == "error" and "unable to access" not in msg["message"].lower():
                return "Cannot download file and didn't hit authentication request for file: " + full_path

    return "All good"


def examine(dataset):

    # Root directory can be projects or investigators
    root_dir = "projects" if dataset in listdir("projects") else "investigators"
    full_dir = join(root_dir, dataset)

    # Check if dats.json and README.md are present in root of dataset
    file_names = [file_name.lower() for file_name in listdir(full_dir)]
    if "dats.json" not in file_names:
        return "Dataset " + full_dir + " doesn't contain dats.json in its root directory"

    if "readme.md" not in file_names:
        return "Dataset " + full_dir + " doesn't contain README.md in its root directory"

    # Number of files to test in each dataset
    # with 100 files, the test is not completing before Travis timeout (about 10~12 minutes)
    num_files = 4
    
    # Count the number of testable files while ignoring files in directories starting with "."
    count = sum([len(files) if basename(dirname(r))[0] != "." else 0 for r, d, files in walk(full_dir)])

    # Calculate the odds to test a file
    odds = num_files/count

    # Start to test dataset
    return recurse(abspath(full_dir), odds)
