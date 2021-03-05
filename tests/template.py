"""Template to base the test of the datasets.
"""
import json
import os
import time
from threading import Lock

from datalad import api
import git
import pytest

from scripts.dats_validator.validator import (
    validate_json,
    validate_non_schema_required,
    validate_formats,
    validate_date_types,
)
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

        if "DATS.json" not in os.listdir(dataset):
            pytest.fail(
                f"Dataset {dataset} doesn't contain DATS.json in its root directory.",
                pytrace=False,
            )

        with open(os.path.join(dataset, "DATS.json")) as fin:
            dats = json.load(fin)

        derivedFrom_url = set()
        if "extraProperties" in dats:
            for property_ in dats["extraProperties"]:
                if property_["category"] == "derivedFrom":
                    derivedFrom_url = {x["value"] for x in property_["values"]}
                break

        submodules = git.Repo(dataset).submodules
        # Parent dataset should not be tested once; in their own dataset repository.
        # For this reason we only install submodules for which there is no derivedFrom
        # value associated with.
        filtered_submodules = [
            submodule.path
            for submodule in submodules
            if submodule.url in derivedFrom_url
        ]

        with lock:
            if len(os.listdir(dataset)) == 0:
                api.install(path=dataset, recursive=False)
            for submodule in filtered_submodules:
                api.install(path=submodule, recursive=True)
        yield

    def test_has_readme(self, dataset):
        if "README.md" not in os.listdir(dataset):
            pytest.fail(
                f"Dataset {dataset} doesn't contain README.md in its root directory.",
                pytrace=False,
            )

    def test_has_valid_dats(self, dataset):

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
                    pytest.fail(
                        summary_error_message,
                        pytrace=False,
                    )

            # For crawled dataset, some tests should not be run as there is no way to
            # automatically populate some of the fields
            # For datasets crawled with Zenodo: check the formats extra property only
            # For datasets crawled with OSF: skip validation of extra properties
            is_osf_dataset = os.path.exists(
                os.path.join(dataset, ".conp-osf-crawler.json")
            )
            is_zenodo_dataset = os.path.exists(
                os.path.join(dataset, ".conp-zenodo-crawler.json")
            )
            is_valid, errors = (
                validate_formats(json_obj)
                if is_zenodo_dataset
                else validate_non_schema_required(json_obj)
            )
            if not is_valid and not is_osf_dataset:
                summary_error_message = (
                    f"Dataset {dataset} contains DATS.json that has errors "
                    f"in required extra properties or formats. List of errors:\n"
                )
                for i, error_message in enumerate(errors, 1):
                    summary_error_message += f"- {i}. {error_message}\n"
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
                "\nCannot determine if the test is valid."
            )
