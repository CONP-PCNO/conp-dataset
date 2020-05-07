from contextlib import contextmanager
from functools import reduce
import json
import os
import random
import re
import signal
import sys
from typing import List, Set, Union

import datalad.api as api
import git
from git.exc import InvalidGitRepositoryError
import keyring
import pytest

from scripts.dats_validator.validator import validate_json


@contextmanager
def timeout(time):
    def raise_timeout(signum, frame):
        raise TimeoutError

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


def project_name2env(project_name: str) -> str:
    """Convert the project name to a valid ENV var name.

    The ENV name for the project must match the regex `[a-zA-Z_]+[a-zA-Z0-9_]*`.

    Parameters
    ----------
    project_name: str
        Name of the project.

    Return
    ------
    project_env: str
        A valid ENV name for the project.
    """
    project_name = project_name.replace("-", "_")
    project_env = re.sub("[_]+", "_", project_name)  # Remove consecutive `_`
    project_env = re.sub("[^a-zA-Z0-9_]", "", project_env)

    # Env var cannot start with number
    if re.compile("[0-9]").match(project_env[0]):
        project_env = "_" + project_env

    return project_env.upper()


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
    try:
        info_output = git.Repo(dataset).git.annex(
            "info", os.path.join(dataset, file_path), json=True, bytes=True,
        )
        metadata = json.loads(info_output)
        return int(metadata["size"])
    except Exception as e:
        print(e)
    # Failed to retrieve file size.
    return float("inf")


def remove_ftp_files(dataset: str, filenames: list) -> list:
    """Remove files that only use ftp as a remote.
    
    Parameters
    ----------
    dataset : str
        Path to the dataset containing the files.
    filenames : List[str]
        List of filenames path in the dataset.
    
    Returns
    -------
    files_without_ftp : list
        List of filenames path not using ftp.
    """
    files_without_ftp = []
    for filename in filenames:
        try:
            whereis_output = git.Repo(dataset).git.annex(
                "whereis", os.path.join(dataset, filename), json=True
            )
            whereis = json.loads(whereis_output)

        except Exception as e:
            print(e)

        urls_without_ftp = [
            url
            for x in whereis["whereis"]
            for url in x["urls"]
            if not url.startswith("ftp://")
        ]

        if len(urls_without_ftp) > 0:
            files_without_ftp.append(filename)

    return files_without_ftp


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
    try:
        with open(os.path.join(dataset, "DATS.json"), "rb") as fin:
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
                print(f"{str(e)} field not found in DATS.json")

    except FileNotFoundError as e:
        pytest.fail(f"DATS.json was not found!\n{str(e)}", pytrace=False)
    except Exeception as e:
        pytest.fail(f"Authentiaction error!\n{str(e)}", pytrace=False)


def generate_datalad_provider(loris_api):

    # Regex for provider
    re_loris_api = loris_api.replace(".", "\.")

    datalad_provider_path = os.path.join(
        os.path.expanduser("~"), ".config", "datalad", "providers"
    )
    os.makedirs(datalad_provider_path, exist_ok=True)
    with open(os.path.join(datalad_provider_path, "loris.cfg"), "w+",) as fout:
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


def get_all_submodules(root: str) -> set:
    """Return recursively all submodule of a dataset.
    
    Parameters
    ----------
    root : str
        Absolute path of the submodule root.
    
    Returns
    -------
    set
        All submodules path of a dataset.
    """
    try:
        submodules: Union[Set[str], None] = {
            os.path.join(root, submodule.path)
            for submodule in git.Repo(root).submodules
        }
    except InvalidGitRepositoryError as e:
        submodules = None

    if submodules:
        rv = reduce(
            lambda x, y: x.union(y),
            [
                get_all_submodules(os.path.join(root, str(submodule)))
                for submodule in submodules
            ],
        )
        return rv | submodules
    else:
        return set()


def authenticate(dataset):
    # If authentication is required and credentials are provided then add credentials
    # to the keyring and create a provider config file.
    # Note: Assume a loris-token authentication.
    project = project_name2env(dataset.split("/")[-1])

    username = os.getenv(project + "_USERNAME", None)
    password = os.getenv(project + "_PASSWORD", None)
    loris_api = os.getenv(project + "_LORIS_API", None)
    zenodo_token = os.getenv(project + "_ZENODO_TOKEN", None)

    if username and password and loris_api:
        keyring.set_password("datalad-loris", "user", username)
        keyring.set_password("datalad-loris", "password", password)
        generate_datalad_provider(loris_api)
    elif zenodo_token:
        pass
    elif is_authentication_required(dataset) == True:
        if os.getenv("TRAVIS_EVENT_TYPE", None) == "pull_request" or os.getenv(
            "CIRCLE_PR_NUMBER", False
        ):
            pytest.skip(
                f"WARNING: {dataset} cannot be test on Pull Requests to protect secrets."
            )

        pytest.fail(
            "Cannot download file (dataset requires authentication, make sure "
            + f"that environment variables {project}_USERNAME, {project}_PASSWORD, "
            + f"and {project}_LORIS_API are defined in Travis).",
            pytrace=False,
        )


def get_filenames(dataset):
    annex_list: str = git.Repo(dataset).git.annex("list")
    filenames: List[str] = re.split(r"\n[_X]+\s", annex_list)[1:]

    submodules: Set[str] = get_all_submodules(dataset)
    for submodule in submodules:
        annex_list = git.Repo(submodule).git.annex("list")
        filenames += [
            os.path.join(submodule, filename)
            for filename in re.split(r"\n[_X]+\s", annex_list)[1:]
        ]
    return filenames


def download_files(dataset, filenames, time_limit=120):
    responses = []
    with timeout(time_limit):
        for filename in filenames:
            full_path = os.path.join(dataset, filename)
            responses = api.get(path=full_path, on_failure="ignore")

            for response in responses:
                if response.get("status") in ["ok", "notneeded"]:
                    continue
                if response.get("status") in ["impossible", "error"]:
                    pytest.fail(
                        f"{full_path}\n{response.get('message')}", pytrace=False
                    )

    if responses == []:
        pytest.fail(
            f"The dataset timed out after {time_limit} seconds before retrieving a file."
            + " Cannot to tell if the download would be sucessful."
            + f"\n{filename} has size of {get_annexed_file_size(dataset, full_path)} Bytes.",
            pytrace=False,
        )


def get_approx_ksmallests(dataset, filenames, k=4, sample_size=200):
    # Take random sample of the filenames to avoid timeout or long test runs.
    #
    # Setting the seed to the concatenation of filenames allow to have randomness when
    # the dataset is updated, while keeping consistency when the state of the dataset
    # stays the same.
    random.seed("".join(filenames))
    sample_files = random.sample(filenames, min(sample_size, len(filenames)))

    # Return the k smallest files from sample
    return sorted(
        [filename for filename in sample_files],
        key=lambda x: get_annexed_file_size(dataset, x),
    )[:k]
