from contextlib import contextmanager
import json
import os
from random import sample
import re
import signal
import sys

import datalad.api as api
from git import Repo
import keyring

from scripts.dats_validator.validator import validate_json


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


def is_authentication_required(dataset):
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


def examine(dataset, project):

    file_names = [file_name for file_name in os.listdir(dataset)]

    if "README.md" not in file_names:
        return "Dataset " + dataset + " doesn't contain README.md in its root directory"

    if "DATS.json" not in file_names:
        return "Dataset " + dataset + " doesn't contain DATS.json in its root directory"

    with open(os.path.join(dataset, "DATS.json"), "r") as f:
        if not validate_json(json.load(f)):
            return "Dataset " + dataset + " doesn't contain a valid DATS.json"

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
    elif is_authentication_required(dataset) == True:
        if os.getenv("TRAVIS_EVENT_TYPE", None) == "pull_request":
            print(
                f"WARNING: {dataset} cannot be test on Pull Requests to protect secrets.",
                file=sys.stderr,
            )
            return True

        print(
            "Cannot download file (dataset requires authentication, make sure "
            + f"that environment variables {project}_USERNAME, {project}_PASSWORD, "
            + f"and {project}_LORIS_API are defined in Travis)"
        )
        return False

    # Number of files to test in each dataset
    # with 100 files, the test is not completing before Travis timeout (about 10~12 minutes)
    num_files = 4

    # Get list of all annexed files and choose randomly num_files of them to test
    annex_list: str = Repo(dataset).git.annex("list")
    files: list = re.split(r"\n____.* ", annex_list)[1:]
    files: list = sample(files, min(num_files, len(files)))

    if len(files) == 0:
        print("No files found in the annex.")
        return False

    # Test those randomly chose files
    for file in files:
        # Timeouts the download or a hanging authentification
        full_path = os.path.join(dataset, file)
        responses = []
        with timeout(300):
            responses = api.get(path=full_path, on_failure="ignore")

        for response in responses:
            if response.get("status") in ["ok", "notneeded"]:
                continue
            if response.get("status") in ["impossible", "error"]:
                print(response.get("message") + full_path)
                return False

    return True
