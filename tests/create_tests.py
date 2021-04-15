import os
import re
import string
from typing import List

import requests
from git import Repo


def get_datasets():
    datasets: List[str] = list(map(lambda x: x.path, Repo(".").submodules))

    pull_number = os.getenv("CIRCLE_PR_NUMBER", False)
    if pull_number:
        response = requests.get(
            f"https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls/{pull_number}/files",
        )
        pr_files: List[str] = [data["filename"] for data in response.json()]

        return minimal_tests(datasets, pr_files)
    return datasets


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
                if re.match(f"{dataset}/", pr_filename) or pr_filename == dataset:
                    modified_datasets.append(dataset)
                    break
        else:
            if pr_filename.split("/")[0] in WHITELIST_EXACT:
                continue
            if any([filename in pr_filename for filename in WHITELIST]):
                continue
            return datasets

    return modified_datasets


template = string.Template(
    """import pytest

from tests.template import Template


@pytest.mark.parametrize('dataset', ['$dataset'])
class TestDataset(Template):
    pass

""",
)

for dataset in get_datasets():
    if dataset.split("/")[0] in ["projects", "investigators"]:
        with open("tests/test_" + dataset.replace("/", "_") + ".py", "w") as f:

            f.write(template.substitute(dataset=dataset))
