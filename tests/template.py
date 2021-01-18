"""Template to base the test of the datasets.
"""
import json
import os
import time
from threading import Lock

from datalad import api
import git
import pytest

from scripts.dats_validator.validator import validate_json
from scripts.dats_validator.validator import validate_non_schema_required
from tests.functions import (
    authenticate,
    download_files,
    eval_config,
    get_approx_ksmallests,
    get_filenames,
    project_name2env,
    timeout,
)


def delay_rerun(*args):
    time.sleep(5)
    return True


lock = Lock()


class Template(object):
    @pytest.fixture(autouse=True)
    def install_dataset(self, dataset):
        with lock:
            if len(os.listdir(dataset)) == 0:
                api.install(path=dataset, recursive=False)
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

        with open(os.path.join(dataset, "DATS.json"), "rb") as f:
            is_valid, errors = validate_non_schema_required(json.load(f))
            if not is_valid:
                summary_error_message = f"Dataset {dataset} contains DATS.json that has errors "
                                        f"in required extra properties or formats. List of errors:\n",
                for error_message in errors:
                    summary_error_message += f"- {error_message}\n"
                pytest.fail(
                    summary_error_message,
                    pytrace=False,
                )

    def test_download(self, dataset):
        eval_config(dataset)
        authenticate(dataset)

        filenames = get_filenames(dataset)
        if len(filenames) == 0:
            return True

        k_smallest = get_approx_ksmallests(dataset, filenames)

        # Restricted Zenodo datasets require to download the whole archive before
        # downloading individual files.
        project = project_name2env(dataset.split("/")[-1])
        if os.getenv(project + "_ZENODO_TOKEN", None):
            with timeout(300):
                api.get(path=dataset, on_failure="ignore")
        download_files(dataset, k_smallest)

    def test_files_integrity(self, dataset):
        TIME_LIMIT = 300
        completed = False
        with timeout(TIME_LIMIT):
            try:
                # Currently some dataset have DataLad metadata, however, those are
                # out-of-date. Since the datasets are still functional but this leads can
                # lead to test failure, the DataLad metadata are ignore when running fsck.
                #
                # In the future, those metadata are likely to be removed. When this occurs,
                # this the `exclude=".datalad/metadata/**"` argument should be removed.
                fsck_output = git.Repo(dataset).git.annex(
                    "fsck", fast=True, quiet=True, exclude=".datalad/metadata/**",
                )
                if fsck_output:
                    pytest.fail(fsck_output, pytrace=False)
            except Exception as e:
                pytest.fail(str(e), pytrace=False)

            completed = True

        if not completed:
            pytest.fail(
                f"The dataset timed out after {TIME_LIMIT} seconds before retrieving a file."
                + "\nCannot determine if the test is valid."
            )
