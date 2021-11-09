import datetime
import json
import os
import re
from typing import Callable

import html2markdown
import humanize
import requests
from datalad.distribution.dataset import Dataset
from git import Repo

from scripts.Crawlers.BaseCrawler import BaseCrawler


def _create_zenodo_tracker(path, dataset):
    with open(path, "w") as f:
        data = {
            "zenodo": {
                "concept_doi": dataset["concept_doi"],
                "version": dataset["latest_version"],
            },
            "title": dataset["title"],
        }
        json.dump(data, f, indent=4)


def _get_annex(dataset_dir) -> Callable:
    return Repo(dataset_dir).git.annex


class ZenodoCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force, no_pr, basedir):
        super().__init__(github_token, config_path, verbose, force, no_pr, basedir)
        self.zenodo_tokens = self._get_tokens()

    def _get_tokens(self):
        if os.path.isfile(self.config_path):
            with open(self.config_path) as f:
                data = json.load(f)
            if "zenodo_tokens" in data.keys():
                return data["zenodo_tokens"]
            else:
                return {}

    def _query_zenodo(self):
        query = (
            "https://zenodo.org/api/records/?"
            "type=dataset&"
            'q=keywords:"canadian-open-neuroscience-platform"'
        )
        r_json = requests.get(query).json()
        results = r_json["hits"]["hits"]

        if r_json["links"]["next"]:
            next_page = r_json["links"]["next"]
            while next_page is not None:
                next_page_json = requests.get(next_page).json()
                results.extend(next_page_json["hits"]["hits"])
                next_page = (
                    next_page_json["links"]["next"]
                    if "next" in next_page_json["links"]
                    else None
                )

        if self.verbose:
            print("Zenodo query: {}".format(query))
        return results

    def _download_file(self, bucket, d, is_private):
        link: str = (
            bucket["links"]["self"]
            if not is_private
            else bucket["links"]["self"].split("?")[0]
        )
        file_name: str = bucket.get("key", "no name")
        file_size: int = bucket.get("size", 0)
        if self.verbose:
            print(f"Downloading {link} as {file_name} of size {file_size}")
        d.download_url(link, archive=True if bucket["type"] == "zip" else False)

    def get_all_dataset_description(self):
        zenodo_dois = []
        datasets = self._query_zenodo()
        for dataset in datasets:
            metadata = dataset["metadata"]
            clean_title = self._clean_dataset_title(metadata["title"])

            # Retrieve file urls
            files = []
            is_private = False
            dataset_token = ""
            if "files" not in dataset.keys():
                # This means the Zenodo dataset files are restricted
                # Try to see if the dataset token is already known in stored tokens
                if clean_title in self.zenodo_tokens.keys():
                    data = requests.get(
                        dataset["links"]["latest"],
                        params={"access_token": self.zenodo_tokens[clean_title]},
                    ).json()
                    if "files" not in data.keys():
                        print(
                            "Unable to access {} using stored tokens, "
                            "skipping this dataset".format(clean_title),
                        )
                        continue
                    else:
                        # Append access token to each file url
                        for bucket in data["files"]:
                            bucket["links"]["self"] += (
                                "?access_token=" + self.zenodo_tokens[clean_title]
                            )
                            files.append(bucket)
                        is_private = True
                        dataset_token = self.zenodo_tokens[clean_title]
                else:
                    print(
                        "No available tokens to access files of {}".format(
                            metadata["title"],
                        ),
                    )
                    continue
            else:
                for bucket in dataset["files"]:
                    files.append(bucket)

            latest_version_doi = metadata["relations"]["version"][0]["last_child"][
                "pid_value"
            ]

            # Retrieve and clean file formats/extensions
            file_formats = (
                list(set(map(lambda x: x["type"], files))) if len(files) > 0 else None
            )
            if "" in file_formats:
                file_formats.remove("")

            # Retrieve and clean file keywords
            keywords = []
            if "keywords" in metadata.keys():
                keywords = list(map(lambda x: {"value": x}, metadata["keywords"]))

            # Retrieve subject annotations from Zenodo and clean the annotated
            # subjects to insert in isAbout of DATS file
            is_about = []
            if "subjects" in metadata.keys():
                for subject in metadata["subjects"]:
                    if re.match("www.ncbi.nlm.nih.gov/taxonomy", subject["identifier"]):
                        is_about.append(
                            {
                                "identifier": {"identifier": subject["identifier"]},
                                "name": subject["term"],
                            }
                        )
                    else:
                        is_about.append(
                            {
                                "valueIRI": subject["identifier"],
                                "value": subject["term"],
                            }
                        )

            dataset_size, dataset_unit = humanize.naturalsize(
                sum([filename["size"] for filename in files]),
            ).split(" ")
            dataset_size = float(dataset_size)

            # Get creators and assign roles if it exists
            creators = list(map(lambda x: {"name": x["name"]}, metadata["creators"]))
            if "contributors" in metadata.keys():
                for contributor in metadata["contributors"]:
                    if contributor["type"] == "ProjectLeader":
                        for creator in creators:
                            if creator["name"].lower() == contributor["name"].lower():
                                creator["roles"] = [{"value": "Principal Investigator"}]
                                break
                        else:
                            creators.append(
                                {
                                    "name": contributor["name"],
                                    "roles": [{"value": "Principal Investigator"}],
                                },
                            )

            # Get identifier
            identifier = (
                dataset["conceptdoi"]
                if "conceptdoi" in dataset.keys()
                else dataset["doi"]
            )

            # Get date created and date modified
            date_created = datetime.datetime.strptime(
                dataset["created"],
                "%Y-%m-%dT%H:%M:%S.%f%z",
            )
            date_modified = datetime.datetime.strptime(
                dataset["updated"],
                "%Y-%m-%dT%H:%M:%S.%f%z",
            )

            zenodo_dois.append(
                {
                    "identifier": {
                        "identifier": "https://doi.org/{}".format(identifier),
                        "identifierSource": "DOI",
                    },
                    "concept_doi": dataset["conceptrecid"],
                    "latest_version": latest_version_doi,
                    "title": metadata["title"],
                    "files": files,
                    "doi_badge": identifier,
                    "creators": creators,
                    "description": metadata["description"],
                    "version": metadata["version"]
                    if "version" in metadata.keys()
                    else "None",
                    "licenses": [
                        {
                            "name": metadata["license"]["id"]
                            if "license" in metadata.keys()
                            else "None",
                        },
                    ],
                    "is_private": is_private,
                    "dataset_token": dataset_token,
                    "keywords": keywords,
                    "distributions": [
                        {
                            "formats": [
                                file_format.upper()
                                for file_format in file_formats
                                # Do not modify specific file formats.
                                if file_formats not in ["NIfTI", "BigWig"]
                            ],
                            "size": dataset_size,
                            "unit": {"value": dataset_unit},
                            "access": {
                                "landingPage": dataset["links"]["html"],
                                "authorizations": [
                                    {
                                        "value": "public"
                                        if metadata["access_right"] == "open"
                                        else "private",
                                    },
                                ],
                            },
                        },
                    ],
                    "extraProperties": [
                        {
                            "category": "logo",
                            "values": [
                                {
                                    "value": "https://about.zenodo.org/static/img/logos/zenodo-gradient-round.svg",
                                },
                            ],
                        },
                    ],
                    "dates": [
                        {
                            "date": date_created.strftime("%Y-%m-%d %H:%M:%S"),
                            "type": {
                                "value": "date created",
                            },
                        },
                        {
                            "date": date_modified.strftime("%Y-%m-%d %H:%M:%S"),
                            "type": {
                                "value": "date modified",
                            },
                        },
                    ],
                },
            )

        if self.verbose:
            print("Retrieved Zenodo DOIs: ")
            for zenodo_doi in zenodo_dois:
                print(
                    "- Title: {}, Concept DOI: {}, Latest version DOI: {}, Private: {}, Token: {}".format(
                        zenodo_doi["title"],
                        zenodo_doi["concept_doi"],
                        zenodo_doi["latest_version"],
                        zenodo_doi["is_private"],
                        zenodo_doi["dataset_token"],
                    ),
                )

        return zenodo_dois

    def add_new_dataset(self, dataset, dataset_dir):
        d: Dataset = self.datalad.Dataset(dataset_dir)
        d.no_annex(".conp-zenodo-crawler.json")
        d.no_annex("config")
        d.save()
        annex: Callable = _get_annex(dataset_dir)
        is_private: bool = dataset.get("is_private", False)
        dataset_token: str = dataset.get("dataset_token", "")

        if is_private:
            self._setup_private_dataset(dataset_dir, annex, d, dataset_token)

        if self.verbose:
            print(
                f'Adding new dataset {dataset["title"]}, is_private: {is_private}, token: {dataset_token}'
            )

        for bucket in dataset["files"]:
            self._download_file(bucket, d, is_private)

        # Add .conp-zenodo-crawler.json tracker file
        _create_zenodo_tracker(
            os.path.join(dataset_dir, ".conp-zenodo-crawler.json"),
            dataset,
        )

    def update_if_necessary(self, dataset_description, dataset_dir):
        tracker_path = os.path.join(dataset_dir, ".conp-zenodo-crawler.json")
        if not os.path.isfile(tracker_path):
            print("{} does not exist in dataset, skipping".format(tracker_path))
            return False
        with open(tracker_path) as f:
            tracker = json.load(f)
        if tracker["zenodo"]["version"] == dataset_description["latest_version"]:
            # Same version, no need to update
            if self.verbose:
                print(
                    "{}, version {} same as Zenodo vesion DOI, no need to update".format(
                        dataset_description["title"],
                        dataset_description["latest_version"],
                    ),
                )
            return False
        else:
            # Update dataset
            if self.verbose:
                print(
                    f"{dataset_description['title']}, version {tracker['zenodo']['version']} different "
                    f"from Zenodo vesion DOI {dataset_description['latest_version']}, updating",
                )

            # Remove all data and DATS.json files
            for file_name in os.listdir(dataset_dir):
                if file_name[0] == ".":
                    continue
                self.datalad.remove(os.path.join(dataset_dir, file_name), check=False)

            d: Dataset = self.datalad.Dataset(dataset_dir)
            is_private: bool = dataset_description.get("is_private", False)

            # For download authentication purposes
            if is_private:
                dataset_token: str = dataset_description.get("dataset_token", "")
                if self.verbose:
                    print(f"Setting DATALAD_ZENODO_token={dataset_token}")
                os.environ["DATALAD_ZENODO_token"] = dataset_token

            for bucket in dataset_description["files"]:
                self._download_file(bucket, d, is_private)

            # Add/update .conp-zenodo-crawler.json tracker file
            _create_zenodo_tracker(
                tracker_path,
                dataset_description,
            )

            return True

    def get_readme_content(self, dataset):
        return """# {0}

[![DOI](https://www.zenodo.org/badge/DOI/{1}.svg)](https://doi.org/{1})

Crawled from Zenodo

## Description

{2}""".format(
            dataset["title"],
            dataset["doi_badge"],
            html2markdown.convert(
                dataset["description"],
            ).replace("\n", "<br />"),
        )

    def _setup_private_dataset(
        self,
        dataset_dir: str,
        annex: Callable,
        dataset: Dataset,
        dataset_token: str,
    ):
        if self.verbose:
            print(
                "Dataset is private, creating Zenodo provider and make git annex autoenable datalad remote",
            )

        # Create Zenodo provider file and needed directories and don't annex the file
        datalad_dir: str = os.path.join(dataset_dir, ".datalad")
        if not os.path.exists(datalad_dir):
            os.mkdir(datalad_dir)
        providers_dir: str = os.path.join(datalad_dir, "providers")
        if not os.path.exists(providers_dir):
            os.mkdir(providers_dir)
        zenodo_config_path: str = os.path.join(providers_dir, "ZENODO.cfg")
        with open(zenodo_config_path, "w") as f:
            f.write(
                """[provider:ZENODO]
url_re = .*zenodo\\.org.*
authentication_type = bearer_token
credential = ZENODO

[credential:ZENODO]
# If known, specify URL or email to how/where to request credentials
# url = ???
type = token"""
            )
        dataset.no_annex(os.path.join("**", "ZENODO.cfg"))

        # Make git annex autoenable datalad remote
        annex(
            "initremote",
            "datalad",
            "externaltype=datalad",
            "type=external",
            "encryption=none",
            "autoenable=true",
        )

        # Set ZENODO token as a environment variable for authentication
        os.environ["DATALAD_ZENODO_token"] = dataset_token

        # Save changes
        dataset.save()
