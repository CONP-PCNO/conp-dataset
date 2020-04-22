"""Template to base the test of the datasets.
"""
import os

import pytest


class Template(object):
    def test_has_readme(self, dataset):
        if "README.md" not in os.listdir(dataset):
            pytest.fail(
                f"Dataset {dataset} doesn't contain README.md in its root directory.",
                pytrace=False,
            )

    def test_has_valid_dats(self, dataset):
        raise NotImplemented

    def test_download(self, dataset):
        raise NotImplemented

    def test_files_integrity(self, dataset):
        raise NotImplemented
