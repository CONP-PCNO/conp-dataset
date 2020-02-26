from contextlib import contextmanager
import json
import os
from os import listdir, walk
from os.path import isdir, exists, join, abspath, basename, dirname
from random import random
import signal

import datalad.api as api
import keyring


@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        pass
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def raise_timeout(signum, frame):
    raise TimeoutError


def is_authentication_require(dataset):
    """Verify in the dataset DATS file if authentication is required.
    
    Parameters
    ----------
    dataset : str
        Relative path to the dataset root.
    
    Returns
    -------
    bool
        Wether the dataset requires authentication.
    """
    with open(os.path.join(dataset, "DATS.json")) as fin:
        metadata = json.load(fin)

        try:
            distributions = metadata["distributions"]
            for distrubtion in distributions:
                authorizations = distrubtion["access"]["authorizations"]
                if any(
                    [
                        authorization["value"] != "public"
                        for authorization in authorizations
                    ]
                ):
                    return True

            return False
        except KeyError as e:
            return str(e) + " DATS.json is invalid!"


def generate_datalad_provider(loris_api):

    # Regex for provider
    re_loris_api = loris_api.replace(".", "\.")

    with open(
        os.path.join(
            os.path.expanduser("~"), ".config", "datalad", "providers", "loris.cfg"
        ),
        "w",
    ) as fout:
        fout.write(
            f"""[provider:loris]                                                                    
url_re = {re_loris_api}/*                             
authentication_type = loris-token                                                           
credential = loris                                                                  
                                                                                            
[credential:loris]                                                                  
url = {loris_api}/login                                           
type = loris-token  
"""
        )


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
            # Timeouts the download or a hanging authentification
            response = dict()
            with timeout(3):
                response = api.get(
                    path=full_path, on_failure="ignore", return_type="item-or-list"
                )

            if response.get("status") in ["ok", "notneeded"]:
                continue
            if response.get("status") in ["impossible", "error"]:
                return response.get("message") + full_path

    return "All good"


def examine(dataset, project):

    # If authentication is required and credentials are provided then add credentials
    # to the keyring and create a provider config file.
    # Note: Assume a loris-token authentication.
    username = os.getenv(project + "_USERNAME", None)
    password = os.getenv(project + "_PASSWORD", None)
    loris_api = os.getenv(project + "_LORIS_API", None)

    if username and password and loris_api:
        keyring.set_password("datalad-loris", "user", username)
        keyring.set_password("datalad-loris", "password", password)
        generate_datalad_provider(loris_api)
    elif is_authentication_require(dataset) == True:
        return (
            f"Cannot download file (dataset requires authentication, make sure "
            + "that environment variables {project}_USERNAME, {prject}_PASSWORD, "
            + "and {projet}_LORIS_API are defined in Travis)"
        )

    # Check if dats.json and README.md are present in root of dataset
    file_names = [file_name for file_name in listdir(dataset)]
    if "DATS.json" not in file_names:
        return "Dataset " + dataset + " doesn't contain DATS.json in its root directory"

    if "README.md" not in file_names:
        return "Dataset " + dataset + " doesn't contain README.md in its root directory"

    # Number of files to test in each dataset
    # with 100 files, the test is not completing before Travis timeout (about 10~12 minutes)
    num_files = 4

    # Count the number of testable files while ignoring files in directories starting with "."
    count = sum(
        [
            len(files) if basename(dirname(r))[0] != "." else 0
            for r, d, files in walk(dataset)
        ]
    )

    # Calculate the odds to test a file
    odds = num_files / count

    # Start to test dataset
    return recurse(abspath(dataset), odds)
