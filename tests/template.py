"""Template to base the test of the datasets.
"""
import json
import os
import time
from threading import Lock

import git
import humanfriendly
import pytest
from datalad import api

from scripts.dats_validator.validator import validate_date_types
from scripts.dats_validator.validator import validate_is_about
from scripts.dats_validator.validator import validate_json
from scripts.dats_validator.validator import validate_non_schema_required
from scripts.dats_validator.validator import validate_privacy
from tests.constants import RETROSPECTIVE_CRAWLED_DATASET_LIST
from tests.functions import authenticate
from tests.functions import download_files
from tests.functions import eval_config
from tests.functions import get_proper_submodules
from tests.functions import timeout


def delay_rerun(*args):
    time.sleep(5)
    return True


lock = Lock()


class Template:
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

        # skip DATS tests for retrospectively crawled datasets
        if dataset in RETROSPECTIVE_CRAWLED_DATASET_LIST:
            return

        with open(os.path.join(dataset, "DATS.json"), "rb") as f:
            json_obj = json.load(f)
            if not validate_json(json_obj):
                pytest.fail(
                    f"Dataset {dataset} doesn't contain a valid DATS.json.",
                    pytrace=False,
                )

            # Validate the date type values
            date_type_valid_bool, date_type_errors = validate_date_types(json_obj)
            if not date_type_valid_bool:
                summary_error_message = (
                    f"Dataset {dataset} contains DATS.json that has errors "
                    f"in date's type encoding. List of errors:\n"
                )
                for i, error_message in enumerate(date_type_errors, 1):
                    summary_error_message += f"- {i}. {error_message}\n"
                    pytest.fail(summary_error_message, pytrace=False)

            # Validate the privacy values
            privacy_valid_bool, privacy_errors = validate_privacy(json_obj)
            if not privacy_valid_bool:
                summary_error_message = (
                    f"Dataset {dataset} contains DATS.json that has errors "
                    f"in privacy value. Error is:\n"
                    f"- {privacy_errors[0]}"
                )
                pytest.fail(summary_error_message, pytrace=False)

            # Validate that isAbout contains at least one species entry if present
            is_about_valid_bool, is_about_errors = validate_is_about(json_obj)
            if not is_about_valid_bool:
                summary_error_message = (
                    f"Dataset {dataset} contains DATS.json that has errors "
                    f"in isAbout. Error is:\n"
                    f"- {is_about_errors[0]}"
                )
                pytest.fail(summary_error_message, pytrace=False)

            # Perform the extra validation checks
            is_valid, errors = validate_non_schema_required(json_obj)
            if not is_valid:
                summary_error_message = (
                    f"Dataset {dataset} contains DATS.json that has errors "
                    f"in required extra properties or formats. List of errors:\n"
                )
                for i, error_message in enumerate(errors, 1):
                    summary_error_message += f"- {i}. {error_message}\n"
                pytest.fail(summary_error_message, pytrace=False)

    def test_download(self, dataset):
        eval_config(dataset)
        authenticate(dataset)

        with open(os.path.join(dataset, "DATS.json"), "rb") as fin:
            dats = json.load(fin)
            dataset_size: float = 0.0

            for distribution in dats.get("distributions", list()):
                dataset_size += humanfriendly.parse_size(
                    f"{distribution['size']} {distribution['unit']['value']}",
                )

        download_files(dataset, dataset_size)

        # Test the download of proper submodules.
        for submodule in get_proper_submodules(dataset):
            download_files(submodule, dataset_size)

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
                    "fsck",
                    fast=True,
                    quiet=True,
                    exclude=".datalad/metadata/**",
                )
                if fsck_output:
                    pytest.fail(fsck_output, pytrace=False)
            except Exception as e:
                pytest.fail(str(e), pytrace=False)

            completed = True

        if not completed:
            pytest.fail(
                f"The dataset timed out after {TIME_LIMIT} seconds before retrieving a file."
                "\nCannot determine if the test is valid.",
            )
