import os
import re
from string import Template
from typing import List
from git import Repo
import requests


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


def minimal_tests(datasets: List[str], pr_files: List[str]):
    """Return the minimal test set for a pull request.

    To return the dataset affected by a pull request changes we verify if the pull 
    request modifies a file from the dataset. Otherwise, we verify if the file is part
    of a whitelist that does not require testing. If either are the case, we need to 
    test all datasets.
     

    Parameters
    ----------
    datasets : List[str]
        List of datasets in the repository.
    pr_files : List[str]
        List of files modified by the pull request.
    
    Returns
    -------
    list
        List of dataset affected by the pull request cheanges.
    """
    WHITELIST_EXACT: List[str] = [
        ".datalad",
        "docs",
        "metadata",
    ]
    WHITELIST: List[str] = [".git", "README", "LICENSE", "requirements.txt"]

    # No need to do tests when no modification are brought.
    if len(pr_files) == 0:
        return []

    modified_datasets: List[str] = []
    for pr_filename in pr_files:
        if pr_filename.startswith("projects/"):
            for dataset in datasets:
                if re.match(f"{dataset}\/", pr_filename) or pr_filename == dataset:
                    modified_datasets.append(dataset)
                    break
        else:
            if pr_filename.split("/")[0] in WHITELIST_EXACT:
                continue
            if any([filename in pr_filename for filename in WHITELIST]):
                continue
            return datasets

    return modified_datasets


template = Template(
    """from functions import examine


def test_$clean_title():
    assert examine('$path', '$project')
"""
)

datasets: List[str] = list(map(lambda x: x.path, Repo(".").submodules))

# Detect if we should skip tests for a dataset.
# This prevent all dataset to be tested on every PR build.
if os.getenv("TRAVIS", False):
    pull_number = os.getenv("TRAVIS_PULL_REQUEST")
    pull_number = False if pull_number == "false" else pull_number
elif os.getenv("CIRCLECI", False):
    pull_number = os.getenv("CIRCLE_PR_NUMBER", False)
else:
    pull_number = False

if pull_number:
    response = requests.get(
        f"https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls/{pull_number}/files"
    )
    pr_files: List[str] = [data["filename"] for data in response.json()]

    datasets = minimal_tests(datasets, pr_files)

for dataset in datasets:
    if dataset.split("/")[0] == "projects" or dataset.split("/")[0] == "investigators":
        with open("tests/test_" + dataset.replace("/", "_") + ".py", "w") as f:

            dataset_path = os.path.join(
                os.getenv("TRAVIS_BUILD_DIR", os.getcwd()), dataset
            )
            f.write(
                template.substitute(
                    path=dataset_path,
                    project=project_name2env(dataset.split("/")[-1]),
                    clean_title=dataset.replace("/", "_").replace("-", "_"),
                )
            )
