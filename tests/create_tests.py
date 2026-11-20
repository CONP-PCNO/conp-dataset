import json
import os
import re
import string

import requests
from git import Repo


def get_datasets():
    datasets: list[str] = list(map(lambda x: x.path, Repo(".").submodules))

    if os.getenv("GITHUB_EVENT_NAME") == "pull_request":
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise RuntimeError(
                "GITHUB_EVENT_PATH is required for pull request test selection."
            )
        with open(event_path) as event_file:
            pull_number = json.load(event_file)["pull_request"]["number"]

        repository = os.getenv("GITHUB_REPOSITORY", "CONP-PCNO/conp-dataset")
        next_url = (
            f"https://api.github.com/repos/{repository}/pulls/{pull_number}/files"
            "?per_page=100"
        )
        headers = {"Accept": "application/vnd.github+json"}
        if token := os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"

        pr_files = []
        while next_url:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
            pr_files.extend(data["filename"] for data in response.json())
            next_url = response.links.get("next", {}).get("url")

        return minimal_tests(datasets, pr_files)
    return datasets


def minimal_tests(datasets: list[str], pr_files: list[str]):
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
    WHITELIST_EXACT: list[str] = [
        ".datalad",
        "docs",
        "metadata",
    ]
    WHITELIST: list[str] = [
        ".git",
        "README",
        "LICENSE",
        "pyproject.toml",
        "uv.lock",
    ]

    # No need to do tests when no modification are brought.
    if len(pr_files) == 0:
        return []

    modified_datasets: list[str] = []
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
