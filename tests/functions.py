from os import listdir, walk
from os.path import isdir, exists, join, abspath
from random import random
import datalad.api as api
import subprocess


def test_recurse(directory, odds):

    # Get all file names in directory
    files = listdir(directory)

    # Loop throw every file
    for file in files:

        # Execute any config.sh scripts
        if file == "config.sh":
            with open(file, "r") as f:
                line = f.readline()
                while line:
                    subprocess.call(line)
                    line = f.readline()
            continue

        # If the file starts with ".", has descriptor or readme in filename, continue onto next file
        if file[0] == "." or \
            "descriptor" in file.lower() or \
            "readme" in file.lower():
            continue

        full_path = join(directory, file)

        # If the file is a directory
        if isdir(full_path):

            result = test_recurse(full_path, odds)

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
            if msg["status"] == "error" and \
                "unable to access" not in msg["message"].lower() and \
                "not available" not in msg["message"].lower():
                return "No authentication setup for file: " + full_path

    return "All good"


def test(dataset):

    # Number of files to test in each dataset
    num_files = 100

    # Root directory can be projects or investigators
    root_dir = "projects" if dataset in listdir("projects") else "investigators"

    # Count the number of testable files while ignoring files in directories starting with "."
    count = sum([len(files) if r.split("/")[-1][0] != "." else 0 for r, d, files in walk(root_dir + "/" + dataset)])

    # Calculate the odds to test a file
    odds = num_files/count

    # Start to test dataset
    return test_recurse(abspath(root_dir + "/" + dataset), odds)
