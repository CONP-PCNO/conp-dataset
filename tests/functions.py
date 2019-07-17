from os import listdir, walk
from os.path import isdir, exists, join, abspath, basename, dirname
from random import random
import datalad.api as api


def recurse(directory, odds):

    # Get all file names in directory
    files = listdir(directory)

    # Loop throw every file
    for file_name in files:

        # If the file name is .git or .datalad, ignore
        if file_name == ".git" or file_name == ".datalad":
            continue

        full_path = join(directory, file_name)

        # If the file is a directory
        if isdir(full_path):

            result = recurse(full_path, odds)

            if result != "All good":
                return result

        # If the file is a broken symlink and with odd chance
        elif not exists(full_path) and random() < odds:
            msg = api.get(path=full_path, on_failure="ignore", return_type="item-or-list")

            # Check for URL in each file
            if "annexkey" in msg.keys():
                if "URL" not in msg["annexkey"]:
                    return "No URL in annexkey: " + msg["annexkey"] + " for file: " + full_path
            else:
                return "No annexkey in file: " + full_path

            # Check for authentication
            if (msg["status"] == "error" and
                    "unable to access" not in msg["message"].lower() and
                    "not available" not in msg["message"].lower()):
                return "No authentication setup for file: " + full_path

    return "All good"


def examine(dataset):

    # Root directory can be projects or investigators
    root_dir = "projects" if dataset in listdir("projects") else "investigators"
    full_dir = join(root_dir, dataset)

    # Check if dats.json and README.md are present in root of dataset
    # if "dats.json" not in listdir(full_dir):
    #     return "Dataset " + full_dir + " doesn't contain dats.json in its root directory"
    #
    # if "README.md" not in listdir(full_dir):
    #     return "Dataset " + full_dir + " doesn't contain README.md in its root directory"

    # Number of files to test in each dataset
    num_files = 100

    # Count the number of testable files while ignoring files in directories starting with "."
    count = sum([len(files) if basename(dirname(r))[0] != "." else 0 for r, d, files in walk(full_dir)])

    # Calculate the odds to test a file
    odds = num_files/count

    # Start to test dataset
    return recurse(abspath(full_dir), odds)
