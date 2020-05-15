"""Template to base the test of the datasets.
"""
import json
import os
from threading import Lock
import time

from datalad import api
from flaky import flaky
import git
import pytest

from scripts.dats_validator.validator import validate_json
from tests.functions import (
    authenticate,
    download_files,
    get_approx_ksmallests,
    get_filenames,
    remove_ftp_files,
)


def delay_rerun(*args):
    time.sleep(5)
    return True


lock = Lock()


@pytest.mark.flaky(max_runs=3, rerun_filter=delay_rerun)
class Template(object):
    @pytest.fixture(autouse=True)
    def install_dataset(self, dataset):
        try:
            submodule = [
                submodule
                for submodule in git.Repo().submodules
                if dataset.endswith(submodule.path)
            ][0]

            with lock:
                if len(os.listdir(dataset)) == 0:
                    api.install(path=dataset, source=submodule.url, recursive=True)
        except Exception as e:
            pytest.fail(
                f"Failed to install {dataset} using datalad install.", pytrace=False
            )
        yield

    def test_has_readme(self, dataset):
        if "README.md" not in os.listdir(dataset):
            pytest.fail(
                f"Dataset {dataset} doesn't contain README.md in its root directory.",
                pytrace=False,
            )

    def test_has_valid_dats(self, dataset):
        if "DATS.json" not in os.listdir(dataset):
            pytest.fail(
                f"Dataset {dataset} doesn't contain DATS.json in its root directory.",
                pytrace=False,
            )

        with open(os.path.join(dataset, "DATS.json"), "rb") as f:
            if not validate_json(json.load(f)):
                pytest.fail(
                    f"Dataset {dataset} doesn't contain a valid DATS.json.",
                    pytrace=False,
                )

    def test_download(self, dataset):
        authenticate(dataset)

        filenames = get_filenames(dataset)
        if len(filenames) == 0:
            return True

        # Remove files using FTP as it is unstable in travis.
        if os.getenv("TRAVIS", False):
            filenames = remove_ftp_files(dataset, filenames)

            if len(filenames) == 0:
                pytest.skip(
                    f"WARNING: {dataset} only contains files using FTP."
                    + " Due to Travis limitation we cannot test this dataset."
                )

        download_files(dataset, get_approx_ksmallests(dataset, filenames))

    def test_files_integrity(self, dataset):
        try:
            fsck_output = git.Repo(dataset).git.annex(
                "fsck",
                json=True,
                json_error_messages=True,
                fast=True,
                quiet=True,
            )
            if fsck_output:
                pytest.fail(fsck_output, pytrace=False)
        except Exception as e:
            pytest.fail(str(e), pytrace=False)
