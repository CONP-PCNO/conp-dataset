from unittest import mock
from unittest import TestCase

from scripts.Crawlers.OSFCrawler import OSFCrawler


class TestOSFCrawler(TestCase):
    @mock.patch("scripts.Crawlers.OSFCrawler.OSFCrawler._push_and_pull_request")
    @mock.patch("scripts.Crawlers.OSFCrawler.OSFCrawler._create_readme")
    @mock.patch("scripts.Crawlers.OSFCrawler.OSFCrawler.get_readme_content")
    @mock.patch("scripts.Crawlers.OSFCrawler.OSFCrawler._create_new_dats")
    @mock.patch("scripts.Crawlers.OSFCrawler._create_osf_tracker")
    @mock.patch(
        "scripts.Crawlers.OSFCrawler.OSFCrawler.get_all_dataset_description",
        return_value=[],
    )
    @mock.patch(
        "scripts.Crawlers.OSFCrawler.OSFCrawler._check_requirements",
        return_value="username",
    )
    @mock.patch("git.Repo")
    @mock.patch("datalad.api.Dataset")
    def test_create_new_dataset(
        self,
        mock_dataset,
        mock_repo,
        mock_check_requirements,
        mock_get_all_dataset_description,
        mock_create_osf_tracker,
        mock_create_new_dats,
        mock_get_readme,
        mock_create_readme,
        mock_create_pr,
    ):
        try:
            OSFCrawler("github token", "path/to/config", True, False, True, ".").run()
        except Exception as e:
            self.fail("Unexpected Exception raised: " + str(e))
