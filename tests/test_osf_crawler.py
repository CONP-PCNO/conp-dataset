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


class TestDownloadDistributions(TestCase):
    BASE = {
        "size": 0,
        "unit": {"value": "B"},
        "access": {
            "landingPage": "https://osf.io/xwajn/",
            "authorizations": [{"value": "public"}],
        },
    }

    def test_single_project_gets_its_own_zip(self):
        from scripts.Crawlers.OSFCrawler import build_download_distributions

        parts = [
            {
                "kind": "osfstorage",
                "node": "q482e",
                "title": "F",
                "root": True,
                "files": 3,
                "bytes": 10,
            }
        ]
        dists = build_download_distributions(
            self.BASE, parts, 2.8, "GB", "https://osf.io/q482e", True
        )
        self.assertEqual(len(dists), 1)
        self.assertEqual(
            dists[0]["access"]["accessURL"],
            "https://files.us.osf.io/v1/resources/q482e/providers/osfstorage/?zip=",
        )
        self.assertEqual((dists[0]["size"], dists[0]["unit"]["value"]), (2.8, "GB"))

    def test_components_and_addons_are_parts(self):
        from scripts.Crawlers.OSFCrawler import build_download_distributions

        parts = [
            {
                "kind": "osfstorage",
                "node": "qzucv",
                "title": "Participant level contrast maps",
                "root": False,
                "files": 156,
                "bytes": 318_500_000,
            },
            {
                "kind": "osfstorage",
                "node": "8bwys",
                "title": "Behavioral Data",
                "root": False,
                "files": 1,
                "bytes": 22_548,
            },
            {
                "kind": "github",
                "node": "xwajn",
                "title": "N",
                "root": True,
                "files": 4,
                "bytes": 1000,
                "repo": "a/b",
                "repo_url": "https://github.com/a/b",
                "archive": "https://github.com/a/b/archive/refs/heads/main.zip",
            },
            {
                "kind": "gitlab",
                "node": "xwajn",
                "title": "N",
                "root": True,
                "files": 4,
                "bytes": 1000,
                "repo": "a/c",
            },
            {
                "kind": "osfstorage",
                "node": "8mk46",
                "title": "Empty",
                "root": False,
                "files": 0,
                "bytes": 0,
            },
        ]
        dists = build_download_distributions(
            self.BASE, parts, 318.5, "MB", "https://osf.io/xwajn/", True
        )
        self.assertEqual(len(dists), 4)
        self.assertEqual(dists[0]["title"], "Participant level contrast maps")
        self.assertEqual(dists[0]["identifier"]["identifier"], "https://osf.io/qzucv/")
        self.assertTrue(
            dists[0]["access"]["accessURL"].endswith(
                "/qzucv/providers/osfstorage/?zip="
            )
        )
        self.assertEqual(dists[0]["access"]["landingPage"], "https://osf.io/xwajn/")
        self.assertEqual(
            dists[2]["access"]["accessURL"],
            "https://github.com/a/b/archive/refs/heads/main.zip",
        )
        self.assertNotIn("accessURL", dists[3]["access"])
        self.assertEqual(dists[2]["title"], "Code (GitHub: a/b)")
        self.assertEqual(dists[3]["title"], "Code (GitLab: a/c)")

    def test_private_records_get_no_links(self):
        from scripts.Crawlers.OSFCrawler import build_download_distributions

        parts = [
            {
                "kind": "osfstorage",
                "node": "q482e",
                "title": "F",
                "root": True,
                "files": 3,
                "bytes": 10,
            }
        ]
        dists = build_download_distributions(
            self.BASE, parts, 1, "KB", "https://osf.io/q482e", False
        )
        self.assertNotIn("accessURL", dists[0]["access"])
