from scripts.crawl_zenodo import crawl
from unittest import TestCase
import mock
import random
import string
import os


def mock_input():
    token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
    return token, {}, [], False, False


def mock_zenodo_query():
    return [
                {
                    "conceptdoi": "10.5281/zenodo.2586674",
                    "conceptrecid": "1234567",
                    "metadata": {
                        "title": "Generic Title",
                        "creators": ["Someone"],
                        "description": "Generic description",

                        "relations": {
                            "version": [
                                {
                                    "last_child": {
                                        "pid_value": "7654321"
                                    }
                                }
                            ]
                        }
                    },
                    "links": {
                        "html": "https://www.fake.link.com"
                    },
                    "files": [
                        {
                            "links": {
                                "self": "https://www.test.file.com/nofilehere"
                            },
                            "type": "json"
                        }
                    ]
                }
            ]


def mock_get_empty_conp_dois():
    return []


def mock_get_test_dataset_dir():
    return os.path.join("tests", "datasets")


class TestZenodoCrawler(TestCase):

    @mock.patch("scripts.crawl_zenodo.create_zenodo_tracker")
    @mock.patch("scripts.crawl_zenodo.add_description")
    @mock.patch("scripts.crawl_zenodo.switch_branch")
    @mock.patch("scripts.crawl_zenodo.check_requirements", return_value="username")
    @mock.patch("scripts.crawl_zenodo.commit_push_file")
    @mock.patch("scripts.crawl_zenodo.store")
    @mock.patch("scripts.crawl_zenodo.parse_args", return_value=mock_input())
    @mock.patch("scripts.crawl_zenodo.query_zenodo", return_value=mock_zenodo_query())
    @mock.patch("scripts.crawl_zenodo.get_conp_dois", return_value=mock_get_empty_conp_dois())
    @mock.patch("scripts.crawl_zenodo.create_new_dats")
    @mock.patch("scripts.crawl_zenodo.update_gitmodules")
    @mock.patch("scripts.crawl_zenodo.push_and_pull_request")
    @mock.patch("scripts.crawl_zenodo.create_readme", return_value=False)
    @mock.patch("scripts.crawl_zenodo.verify_repository", return_value=True)
    @mock.patch("git.Repo")
    @mock.patch("datalad.api.Dataset")
    @mock.patch("datalad.api.add")
    def test_create_new_dataset(self, mock_datalad_add, mock_dataset, mock_repo, mock_verify_repo,
                                mock_create_readme, mock_push_and_PR, mock_update_submodules,
                                mock_create_new_dats, mock_empty_conp_dois, mock_zenodo_query, mock_input,
                                mock_store, mock_commit_push_file, mock_check_requirements, mock_switch_branch,
                                mock_add_description, mock_create_zenodo_tracker):
        try:
            crawl()
        except Exception as e:
            self.fail("Unexpected Exception raised: " + str(e))

    @mock.patch("scripts.crawl_zenodo.create_zenodo_tracker")
    @mock.patch("scripts.crawl_zenodo.create_new_dats")
    @mock.patch("scripts.crawl_zenodo.add_description")
    @mock.patch("scripts.crawl_zenodo.switch_branch")
    @mock.patch("scripts.crawl_zenodo.check_requirements", return_value="username")
    @mock.patch("scripts.crawl_zenodo.commit_push_file")
    @mock.patch("scripts.crawl_zenodo.store")
    @mock.patch("scripts.crawl_zenodo.parse_args", return_value=mock_input())
    @mock.patch("scripts.crawl_zenodo.query_zenodo", return_value=mock_zenodo_query())
    @mock.patch("scripts.crawl_zenodo.get_dataset_container_dir", return_value=mock_get_test_dataset_dir())
    @mock.patch("scripts.crawl_zenodo.update_gitmodules")
    @mock.patch("scripts.crawl_zenodo.push_and_pull_request")
    @mock.patch("scripts.crawl_zenodo.create_readme", return_value=False)
    @mock.patch("scripts.crawl_zenodo.verify_repository", return_value=True)
    @mock.patch("git.Repo")
    @mock.patch("datalad.api.Dataset")
    @mock.patch("datalad.api.add")
    def test_update_existing_dataset(self, mock_datalad_add, mock_dataset, mock_repo, mock_verify_repo,
                                     mock_create_readme, mock_push_and_PR, mock_update_submodules,
                                     mock_get_test_dataset_dir, mock_zenodo_query,
                                     mock_input, mock_store, mock_commit_push_file, mock_check_requirements,
                                     mock_switch_branch, mock_add_description, mock_create_new_dats,
                                     mock_create_zenodo_tracker):
        try:
            crawl()
        except Exception as e:
            self.fail("Unexpected Exception raised: " + str(e))
