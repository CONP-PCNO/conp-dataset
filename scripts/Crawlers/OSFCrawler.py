from scripts.Crawlers.BaseCrawler import BaseCrawler
from git import Repo
import os
import json
import requests


def _create_osf_tracker(path, dataset):
    with open(path, "w") as f:
        data = {
            "version": dataset["version"],
            "title": dataset["title"]
        }
        json.dump(data, f, indent=4)


class OSFCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force):
        super().__init__(github_token, config_path, verbose, force)

    def _query_osf(self):
        query = (
            'https://api.osf.io/v2/nodes/?filter[tags]=canadian-open-neuroscience-platform'
        )
        results = requests.get(query).json()["data"]
        if self.verbose:
            print("OSF query: {}".format(query))
        return results

    def _download_files(self, link, current_dir, inner_path, d, annex):
        r = requests.get(link)
        files = r.json()["data"]
        for file in files:
            # Handle folders
            if file["attributes"]["kind"] == "folder":
                folder_path = os.path.join(current_dir, file["attributes"]["name"])
                os.mkdir(folder_path)
                self._download_files(
                    file["relationships"]["files"]["links"]["related"]["href"],
                    folder_path,
                    os.path.join(inner_path, file["attributes"]["name"]),
                    d, annex
                )
            # Handle single files
            elif file["attributes"]["kind"] == "file":
                # Handle zip files
                if file["attributes"]["name"].split(".")[-1] == "zip":
                    d.download_url(file["links"]["download"], path=os.path.join(inner_path, ""), archive=True)
                else:
                    annex("addurl", file["links"]["download"], "--fast", "--file",
                          os.path.join(inner_path, file["attributes"]["name"]))
                    d.save()

    def _get_contributors(self, link):
        r = requests.get(link)
        contributors = [
            contributor["embeds"]["users"]["data"]["attributes"]["full_name"]
            for contributor in r.json()["data"]
        ]
        return contributors

    def _get_license(self, link):
        r = requests.get(link)
        return r.json()["data"]["attributes"]["name"]

    def get_all_dataset_description(self):
        osf_dois = []
        datasets = self._query_osf()
        for dataset in datasets:
            attributes = dataset["attributes"]

            # Retrieve keywords/tags
            keywords = list(map(lambda x: {"value": x}, attributes["tags"]))

            # Retrieve contributors/creators
            contributors = self._get_contributors(
                dataset["relationships"]["contributors"]["links"]["related"]["href"])

            # Retrieve license
            license_ = "None"
            if "license" in dataset["relationships"].keys():
                license_ = self._get_license(
                                    dataset["relationships"]
                                    ["license"]["links"]["related"]["href"])

            osf_dois.append(
                {
                    "title": attributes["title"],
                    "files": dataset["relationships"]["files"]["links"]["related"]["href"],
                    "creators": list(
                        map(lambda x: {"name": x}, contributors)
                    ),
                    "description": attributes["description"],
                    "version": attributes["date_modified"],
                    "licenses": [
                        {
                            "name": license_
                        }
                    ],
                    "keywords": keywords,
                    "extraProperties": [
                        {
                            "category": "logo",
                            "values": [
                                {
                                    "value": "https://osf.io/static/img/institutions/shields/cos-shield.png"
                                }
                            ],
                        }
                    ],
                }
            )

        if self.verbose:
            print("Retrieved OSF DOIs: ")
            for osf_doi in osf_dois:
                print(
                    "- Title: {}, Last modified: {}".format(
                        osf_doi["title"],
                        osf_doi["version"]
                    )
                )

        return osf_dois

    def add_new_dataset(self, dataset, dataset_dir):
        d = self.datalad.Dataset(dataset_dir)
        d.no_annex(".conp-osf-crawler.json")
        d.save()
        annex = Repo(dataset_dir).git.annex

        self._download_files(dataset["files"], dataset_dir, "", d, annex)

        # Add .conp-osf-crawler.json tracker file
        _create_osf_tracker(
            os.path.join(dataset_dir, ".conp-osf-crawler.json"), dataset)

    def update_if_necessary(self, dataset_description, dataset_dir):
        tracker_path = os.path.join(dataset_dir, ".conp-osf-crawler.json")
        if not os.path.isfile(tracker_path):
            print("{} does not exist in dataset, skipping".format(tracker_path))
            return False
        with open(tracker_path, "r") as f:
            tracker = json.load(f)
        if tracker["version"] == dataset_description["version"]:
            # Same version, no need to update
            if self.verbose:
                print("{}, version {} same as OSF version DOI, no need to update"
                      .format(dataset_description["title"], dataset_description["version"]))
            return False
        else:
            # Update dataset
            if self.verbose:
                print("{}, version {} different from OSF version DOI {}, updating"
                      .format(dataset_description["title"], tracker["version"], dataset_description["version"]))

            # Remove all data and DATS.json files
            for file_name in os.listdir(dataset_dir):
                if file_name[0] == "." or file_name == "README.md":
                    continue
                self.datalad.remove(os.path.join(dataset_dir, file_name), check=False)

            d = self.datalad.Dataset(dataset_dir)
            annex = Repo(dataset_dir).git.annex

            for file in dataset_description["files"]:
                self._download_files(file, dataset_dir, "", d, annex)

            # Add .conp-osf-crawler.json tracker file
            _create_osf_tracker(
                os.path.join(dataset_dir, ".conp-osf-crawler.json"), dataset_description)

            return True

    def get_readme_content(self, dataset):
        return """# {}

Crawled from OSF

## Description

{}""".format(dataset["title"], dataset["description"])
