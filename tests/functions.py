import json
import os
import random
import re
import signal
import subprocess
from contextlib import contextmanager
from functools import reduce

import datalad.api as api
import git
import humanize
import keyring
import pytest
from git.exc import InvalidGitRepositoryError


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
    info_output = git.Repo(dataset).git.annex(
        "info",
        file_path,
        json=True,
        bytes=True,
    )
    metadata = json.loads(info_output)

    try:
        return int(metadata["size"])
    except Exception:
        return float("inf")


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
                        ],
                    ):
                        return True

                return False
            except KeyError as e:
                print(f"{str(e)} field not found in DATS.json")

    except FileNotFoundError as e:
        pytest.fail(f"DATS.json was not found!\n{str(e)}", pytrace=False)
    except Exception as e:
        pytest.fail(f"Authentication error!\n{str(e)}", pytrace=False)


def generate_datalad_provider(loris_api):

    # Regex for provider
    re_loris_api = loris_api.replace(".", "\\.")

    datalad_provider_path = os.path.join(
        os.path.expanduser("~"),
        ".config",
        "datalad",
        "providers",
    )
    os.makedirs(datalad_provider_path, exist_ok=True)
    with open(
        os.path.join(datalad_provider_path, "loris.cfg"),
        "w+",
    ) as fout:
        fout.write(
            f"""[provider:loris]
url_re = {re_loris_api}/*
authentication_type = loris-token
credential = loris

[credential:loris]
url = {loris_api}/login
type = loris-token
""",
        )


def get_submodules(root: str) -> set:
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
        submodules = {submodule.path for submodule in git.Repo(root).submodules}
    except InvalidGitRepositoryError:
        submodules = None

    if submodules:
        rv = reduce(
            lambda x, y: x.union(y),
            map(
                lambda submodule: get_submodules(os.path.join(root, submodule)),
                submodules,
            ),
        )
        return rv | submodules
    else:
        return set()


def eval_config(dataset: str) -> None:

    if "config" in os.listdir(dataset):
        subprocess.run([os.path.join(dataset, "config")])


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
    elif is_authentication_required(dataset):
        if os.getenv("CIRCLE_PR_NUMBER", False):
            pytest.skip(
                f"WARNING: {dataset} cannot be test on Pull Requests to protect secrets.",
            )

        pytest.fail(
            "Cannot download file (dataset requires authentication, make sure "
            f"that environment variables {project}_USERNAME, {project}_PASSWORD, "
            f"and {project}_LORIS_API are defined in CircleCI).",
            pytrace=False,
        )


def get_filenames(dataset, *, minimum):
    contains_archived_files = False
    annex_list: str = iter(git.Repo(dataset).git.annex("list").split("\n"))
    remotes = []

    # Retrieve remotes from the header.
    for line in annex_list:
        if re.match(r"^\|+$", line):
            break
        remotes.append(re.sub(r"^\|*", "", line))

    if "datalad-archives" in remotes:
        archived_files = []
        independent_files = []
        archive_index = remotes.index("datalad-archives")

        for line in annex_list:
            # Split only for first occurence to prevent failure when filename has spaces.
            in_remote, filename = line.split(" ", maxsplit=1)

            if in_remote[archive_index] == "X":
                archived_files.append(filename)
            else:
                independent_files.append(filename)

        if len(independent_files) > minimum:
            filenames = independent_files
        else:
            contains_archived_files = True
            filenames = archived_files + independent_files

    else:
        filenames = [x.split()[1] for x in annex_list]

    return filenames, contains_archived_files


def download_files(dataset, dataset_size, *, num=4):
    filenames, contains_archived_files = get_filenames(dataset, minimum=num)
    k_smallest = get_approx_ksmallests(dataset, filenames)

    if len(k_smallest) == 0:
        return

    download_size = (
        dataset_size
        if contains_archived_files
        else get_sample_files_size(dataset, k_smallest)
    )
    # Set a time limit based on the download size.
    # Limit between 20 sec and 10 minutes to avoid test to fail/hang.
    time_limit = int(max(20, min(download_size * 1.2 // 2e6, 600)))

    responses = []
    with timeout(time_limit):
        for filename in k_smallest:
            full_path = os.path.join(dataset, filename)
            responses = api.get(path=full_path, on_failure="ignore")

            for response in responses:
                if response.get("status") in ["ok", "notneeded"]:
                    continue
                if response.get("status") in ["impossible", "error"]:
                    pytest.fail(
                        f"{full_path}\n{response.get('message')}",
                        pytrace=False,
                    )

    if not responses:
        pytest.fail(
            f"The dataset timed out after {time_limit} seconds before retrieving a file."
            " Cannot to tell if the download would be sucessful."
            f"\n{filename} has size of {humanize.naturalsize(get_annexed_file_size(dataset, filename))}.",
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


def get_proper_submodules(dataset: str):
    """Install and Return the non-derivative submodules.

    Parameters
    ----------
    dataset: str
        Path to the root of the dataset.

    Returns
    -------
        proper_submodules: list[str]
            Submodules not derived form another CONP dataset.

    """
    if "DATS.json" not in os.listdir(dataset):
        pytest.fail(
            f"Dataset {dataset} doesn't contain DATS.json in its root directory.",
            pytrace=False,
        )

    with open(os.path.join(dataset, "DATS.json")) as fin:
        dats = json.load(fin)

    parent_dataset_ids = set()
    if "extraProperties" in dats:
        for property_ in dats["extraProperties"]:
            if property_["category"] == "parent_dataset_id":
                parent_dataset_ids = {x["value"] for x in property_["values"]}
                break

    submodules = git.Repo(dataset).submodules
    # Parent dataset should not be tested here but in their own dataset repository.
    # For this reason we only install submodules for which there is no derivedFrom
    # value associated with.
    proper_submodules = [
        os.path.join(dataset, submodule.path)
        for submodule in submodules
        if submodule.path not in parent_dataset_ids
    ]

    for submodule in proper_submodules:
        api.install(path=submodule, recursive=True)

    return proper_submodules


def get_sample_files_size(dir_root, files):
    return sum([get_annexed_file_size(dir_root, f) for f in files])
