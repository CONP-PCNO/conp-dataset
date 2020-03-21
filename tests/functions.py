from contextlib import contextmanager
import json
import os
from random import sample
import re
import signal
import sys

import datalad.api as api
import git
import keyring
import pytest

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


def get_annexed_file_size(dataset, file_path):
    """Get the size of an annexed file in Bytes.
    
    Parameters
    ----------
    dataset : string
        Path to the dataset containing the file.
    file_path : str
        Realative path of the file within a dataset
    
    Returns
    -------
    float
        Size of the annexed file in Bytes.
    """
    metadata = json.loads(
        git.Repo(dataset).git.annex(
            "info", os.path.join(dataset, file_path), json=True, bytes=True,
        )
    )

    return int(metadata["size"])


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
        pytest.fail(
            f"Dataset {dataset} doesn't contain README.md in its root directory."
        )

    if "DATS.json" not in file_names:
        pytest.fail(
            f"Dataset {dataset} doesn't contain DATS.json in its root directory."
        )

    with open(os.path.join(dataset, "DATS.json"), "r") as f:
        if not validate_json(json.load(f)):
            pytest.fail(f"Dataset {dataset} doesn't contain a valid DATS.json.")

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
            pytest.skip(
                f"WARNING: {dataset} cannot be test on Pull Requests to protect secrets."
            )

        pytest.fail(
            "Cannot download file (dataset requires authentication, make sure "
            + f"that environment variables {project}_USERNAME, {project}_PASSWORD, "
            + f"and {project}_LORIS_API are defined in Travis)."
        )

    # Get list of all annexed files and choose randomly num_files of them to test
    annex_list: str = git.Repo(dataset).git.annex("list")
    filenames: list = re.split(r"\n[_X]+\s", annex_list)

    # First element from git annex list is not a file.
    if len(filenames) <= 1:
        pytest.fail(
            "No files found in the annex. This dataset does not contain annexed files."
        )
    else:
        filenames = filenames[1:]

    # Sort files by size
    filenames = sorted(
        [
            (filename, get_annexed_file_size(dataset, filename))
            for filename in filenames
        ],
        key=lambda x: x[1],
    )

    # Limit number of files to test in each dataset to avoid Travis to timeout.
    num_files = 4
    filenames = filenames[:num_files]

    responses = []
    TIMEOUT = 120
    with timeout(TIMEOUT):
        for filename, file_size in filenames:
            full_path = os.path.join(dataset, filename)
            responses = api.get(path=full_path, on_failure="ignore")

            for response in responses:
                if response.get("status") in ["ok", "notneeded"]:
                    continue
                if response.get("status") in ["impossible", "error"]:
                    pytest.fail(f"{full_path}\n{response.get('message')}")

    if responses == []:
        pytest.fail(
            f"The dataset timed out after {TIMEOUT} seconds before retrieving a file."
            + " There is not way to tell if the download would be sucessful."
            + f"\n{filename} has size of {file_size} Bytes."
        )

    return True
