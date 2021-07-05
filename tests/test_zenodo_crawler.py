import os
import random
import string
from unittest import mock
from unittest import TestCase

from scripts.Crawlers.ZenodoCrawler import ZenodoCrawler


def mock_input():
    token = "".join(
        [random.choice(string.ascii_letters + string.digits) for n in range(32)],
    )
    return token, {}, [], False, False


def mock_zenodo_query():
    return [
        {
            "conceptdoi": "10.5281/zenodo.2586674",
            "conceptrecid": "1234567",
            "metadata": {
                "title": "Generic Title",
                "creators": [
                    {
                        "name": "Test",
                    },
                ],
                "description": "Generic description",
                "access_right": "open",
                "relations": {
                    "version": [
                        {
                            "last_child": {
                                "pid_value": "7654321",
                            },
                        },
                    ],
                },
            },
            "links": {
                "html": "https://www.fake.link.com",
            },
            "files": [
                {
                    "links": {
                        "self": "https://www.test.file.com/nofilehere",
                    },
                    "type": "json",
                    "size": 45346,
                },
            ],
        },
    ]


def mock_get_empty_conp_dois():
    return []


def mock_get_test_dataset_dir():
    return os.path.join("tests", "datasets")


class TestZenodoCrawler(TestCase):
    @mock.patch(
        "scripts.Crawlers.BaseCrawler.BaseCrawler._check_dats_present",
        return_value=None,
    )
    @mock.patch("scripts.Crawlers.ZenodoCrawler.ZenodoCrawler._push_and_pull_request")
    @mock.patch("scripts.Crawlers.ZenodoCrawler.ZenodoCrawler._create_readme")
    @mock.patch("scripts.Crawlers.ZenodoCrawler.ZenodoCrawler.get_readme_content")
    @mock.patch("scripts.Crawlers.ZenodoCrawler.ZenodoCrawler._create_new_dats")
    @mock.patch("scripts.Crawlers.ZenodoCrawler._create_zenodo_tracker")
    @mock.patch(
        "scripts.Crawlers.ZenodoCrawler.ZenodoCrawler.get_all_dataset_description",
        return_value=[{"title": "Test", "files": []}],
    )
    @mock.patch(
        "scripts.Crawlers.ZenodoCrawler.ZenodoCrawler._check_requirements",
        return_value="username",
    )
    @mock.patch("git.Repo")
    @mock.patch("scripts.Crawlers.ZenodoCrawler._get_annex")
    @mock.patch("datalad.api.Dataset")
    def test_create_new_dataset(
        self,
        mock_dataset,
        mock_get_annex,
        mock_repo,
        mock_check_requirements,
        mock_get_all_dataset_description,
        mock_create_zenodo_tracker,
        mock_create_new_dats,
        mock_get_readme,
        mock_create_readme,
        mock_create_pr,
        mock_check_dats_present,
    ):
        try:
            ZenodoCrawler(
                "github token", "path/to/config", True, False, True, "."
            ).run()
        except Exception as e:
            self.fail("Unexpected Exception raised: " + str(e))
