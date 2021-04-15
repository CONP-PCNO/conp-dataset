import datetime
import json
import os

import html2markdown
import humanize
import requests

from scripts.Crawlers.BaseCrawler import BaseCrawler


def _get_unlock_script():
    with open(os.path.join("scripts", "unlock.py")) as f:
        return f.read()


def _create_zenodo_tracker(path, dataset, private_files, restricted):
    with open(path, "w") as f:
        data = {
            "zenodo": {
                "concept_doi": dataset["concept_doi"],
                "version": dataset["latest_version"],
            },
            "private_files": private_files,
            "restricted": restricted,
            "title": dataset["title"],
        }
        json.dump(data, f, indent=4)


class ZenodoCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force, no_pr):
        super().__init__(github_token, config_path, verbose, force, no_pr)
        self.zenodo_tokens = self._get_tokens()
        self.unlock_script = _get_unlock_script()

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

    def _download_file(self, bucket, d, dataset_dir, private_files):
        link = bucket["links"]["self"]
        repo = self.git.Repo(dataset_dir)
        annex = repo.git.annex
        if bucket["key"] in ["DATS.json", "README.md"]:
            d.download_url(link)
            return
        if "access_token" not in link:
            if bucket["type"] == "zip":
                d.download_url(link, archive=True)
            else:
                annex("addurl", link, "--fast", "--file", link.split("/")[-1])
        else:  # Have to remove token from annex URL
            tokenless_link = link.split("?")[0]
            if bucket["type"] == "zip":
                d.download_url(link, archive=True)
                # Switch to git-annex branch to remove token from URL then switch back
                original_branch = repo.active_branch.name
                repo.git.checkout("git-annex")
                changes = False
                for dir_name, _, files in os.walk(dataset_dir):
                    for file_name in files:
                        file_path = os.path.join(dir_name, file_name)
                        if ".git" in file_path:
                            continue
                        with open(file_path) as f:
                            s = f.read()
                        if link in s:
                            s = s.replace(link, tokenless_link)
                            with open(file_path, "w") as f:
                                f.write(s)
                            changes = True
                            private_files["archive_links"].append(tokenless_link)
                        elif "?access_token=" in s:
                            s = s.split("?access_token=")[0]
                            with open(file_path, "w") as f:
                                f.write(s)
                            changes = True
                if changes:
                    repo.git.add(".")
                    repo.git.commit("-m", "update")
                repo.git.checkout(original_branch)
            else:
                file_name = json.load(annex("addurl", link, "--fast", "--json"))["file"]
                annex("rmurl", file_name, link)
                annex("addurl", tokenless_link, "--file", file_name, "--relaxed")
                private_files["files"].append(
                    {"name": file_name, "link": tokenless_link},
                )
        d.save()

    def _put_unlock_script(self, dataset_dir):
        with open(os.path.join(dataset_dir, "config"), "w") as f:
            f.write(self.unlock_script)
        os.chmod(os.path.join(dataset_dir, "config"), 0o755)

    def get_all_dataset_description(self):
        zenodo_dois = []
        datasets = self._query_zenodo()
        for dataset in datasets:
            metadata = dataset["metadata"]
            clean_title = self._clean_dataset_title(metadata["title"])

            # Retrieve file urls
            files = []
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
                    "- Title: {}, Concept DOI: {}, Latest version DOI: {}".format(
                        zenodo_doi["title"],
                        zenodo_doi["concept_doi"],
                        zenodo_doi["latest_version"],
                    ),
                )

        return zenodo_dois

    def add_new_dataset(self, dataset, dataset_dir):
        d = self.datalad.Dataset(dataset_dir)
        d.no_annex(".conp-zenodo-crawler.json")
        d.no_annex("config")
        d.save()

        private_files = {"archive_links": [], "files": []}
        for bucket in dataset["files"]:
            self._download_file(bucket, d, dataset_dir, private_files)
        restricted_dataset = (
            True
            if len(private_files["archive_links"]) > 0
            or len(
                private_files["files"],
            )
            > 0
            else False
        )

        # If dataset is a restricted dataset, create a script which allows to unlock downloading files in dataset
        if restricted_dataset:
            self._put_unlock_script(dataset_dir)

        # Add .conp-zenodo-crawler.json tracker file
        _create_zenodo_tracker(
            os.path.join(dataset_dir, ".conp-zenodo-crawler.json"),
            dataset,
            private_files,
            restricted_dataset,
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

            d = self.datalad.Dataset(dataset_dir)

            private_files = {"archive_links": [], "files": []}
            for bucket in dataset_description["files"]:
                self._download_file(bucket, d, dataset_dir, private_files)
            restricted_dataset = (
                True
                if len(private_files["archive_links"]) > 0
                or len(
                    private_files["files"],
                )
                > 0
                else False
            )

            # If dataset is a restricted dataset, create a script which allows to unlock downloading files in dataset
            if restricted_dataset:
                self._put_unlock_script(dataset_dir)

            # Add/update .conp-zenodo-crawler.json tracker file
            _create_zenodo_tracker(
                tracker_path,
                dataset_description,
                private_files,
                restricted_dataset,
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
