import datetime
import json
import os
from typing import Any
from typing import Callable
from typing import Dict
from typing import List

import humanize
import requests
from datalad.distribution.dataset import Dataset
from git import Repo

from scripts.Crawlers.BaseCrawler import BaseCrawler


def _create_osf_tracker(path, dataset):
    with open(path, "w") as f:
        data = {
            "version": dataset["version"],
            "title": dataset["title"],
        }
        json.dump(data, f, indent=4)


class OSFCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force, no_pr):
        super().__init__(github_token, config_path, verbose, force, no_pr)
        self.osf_token = self._get_token()

    def _get_token(self):
        if os.path.isfile(self.config_path):
            with open(self.config_path) as f:
                data = json.load(f)
            if "osf_token" in data.keys():
                return data["osf_token"]

    def _get_request_with_bearer_token(self, link, redirect=True):
        header = {"Authorization": f"Bearer {self.osf_token}"}
        r = requests.get(link, headers=header, allow_redirects=redirect)
        if r.ok:
            return r
        else:
            raise Exception(f"Request to {r.url} failed: {r.content}")

    def _query_osf(self):
        query = "https://api.osf.io/v2/nodes/?filter[tags]=canadian-open-neuroscience-platform"
        r_json = self._get_request_with_bearer_token(query).json()
        results = r_json["data"]

        # Retrieve results from other pages
        if r_json["links"]["meta"]["total"] > r_json["links"]["meta"]["per_page"]:
            next_page = r_json["links"]["next"]
            while next_page is not None:
                next_page_json = self._get_request_with_bearer_token(next_page).json()
                results.extend(next_page_json["data"])
                next_page = next_page_json["links"]["next"]

        if self.verbose:
            print("OSF query: {}".format(query))
        return results

    def _download_files(
        self,
        link,
        current_dir,
        inner_path,
        d,
        annex,
        sizes,
        is_private=False,
    ):
        r_json = self._get_request_with_bearer_token(link).json()
        files = r_json["data"]

        # Retrieve the files in the other pages if there are more than 1 page
        if (
            "links" in r_json.keys()
            and r_json["links"]["meta"]["total"] > r_json["links"]["meta"]["per_page"]
        ):
            next_page = r_json["links"]["next"]
            while next_page is not None:
                next_page_json = self._get_request_with_bearer_token(next_page).json()
                files.extend(next_page_json["data"])
                next_page = next_page_json["links"]["next"]

        for file in files:
            # Handle folders
            if file["attributes"]["kind"] == "folder":
                folder_path = os.path.join(current_dir, file["attributes"]["name"])
                os.mkdir(folder_path)
                self._download_files(
                    file["relationships"]["files"]["links"]["related"]["href"],
                    folder_path,
                    os.path.join(inner_path, file["attributes"]["name"]),
                    d,
                    annex,
                    sizes,
                    is_private,
                )

            # Handle single files
            elif file["attributes"]["kind"] == "file":

                # Private dataset/files
                if is_private:
                    correct_download_link = self._get_request_with_bearer_token(
                        file["links"]["download"],
                        redirect=False,
                    ).headers["location"]
                    if "https://accounts.osf.io/login" not in correct_download_link:
                        zip_file = (
                            True
                            if file["attributes"]["name"].split(".")[-1] == "zip"
                            else False
                        )
                        d.download_url(
                            correct_download_link,
                            path=os.path.join(inner_path, ""),
                            archive=zip_file,
                        )
                    else:  # Token did not work for downloading file, return
                        print(
                            f'Unable to download file {file["links"]["download"]} with current token, skipping file',
                        )
                        return

                # Public file
                else:
                    # Handle zip files
                    if file["attributes"]["name"].split(".")[-1] == "zip":
                        d.download_url(
                            file["links"]["download"],
                            path=os.path.join(inner_path, ""),
                            archive=True,
                        )
                    elif file["attributes"]["name"] in ["DATS.json", "README.md"]:
                        d.download_url(
                            file["links"]["download"],
                            path=os.path.join(inner_path, ""),
                        )
                    else:
                        annex(
                            "addurl",
                            file["links"]["download"],
                            "--fast",
                            "--file",
                            os.path.join(inner_path, file["attributes"]["name"]),
                        )
                        d.save()

                # append the size of the downloaded file to the sizes array
                file_size = file["attributes"]["size"]
                if not file_size:
                    # if the file size cannot be found in the OSF API response, then get it from git annex info
                    inner_file_path = os.path.join(
                        inner_path,
                        file["attributes"]["name"],
                    )
                    annex_info_dict = json.loads(
                        annex("info", "--bytes", "--json", inner_file_path),
                    )
                    file_size = int(annex_info_dict.get("size", 0))
                sizes.append(file_size)

    def _download_components(
        self,
        components_list,
        current_dir,
        inner_path,
        d,
        annex,
        dataset_size,
        is_private,
    ):
        # Loop through each available components and download their files
        for component in components_list:
            component_title = self._clean_dataset_title(
                component["attributes"]["title"],
            )
            component_inner_path = os.path.join(
                inner_path,
                "components",
                component_title,
            )
            os.makedirs(os.path.join(current_dir, component_inner_path))
            self._download_files(
                component["relationships"]["files"]["links"]["related"]["href"],
                os.path.join(current_dir, component_inner_path),
                component_inner_path,
                d,
                annex,
                dataset_size,
                is_private,
            )

            # check if the component contains (sub)components, in which case, download the (sub)components data
            subcomponents_list = self._get_components(
                component["relationships"]["children"]["links"]["related"]["href"],
            )
            if subcomponents_list:
                self._download_components(
                    subcomponents_list,
                    current_dir,
                    os.path.join(component_inner_path),
                    d,
                    annex,
                    dataset_size,
                    is_private,
                )

        # Once we have downloaded all the components files, check to see if there are any empty
        # directories (in the case the 'OSF parent' dataset did not have any downloaded files
        list_of_empty_dirs = [
            dirpath
            for (dirpath, dirnames, filenames) in os.walk(current_dir)
            if len(dirnames) == 0 and len(filenames) == 0
        ]
        for empty_dir in list_of_empty_dirs:
            os.rmdir(empty_dir)

    def _get_contributors(self, link):
        r = self._get_request_with_bearer_token(link)
        contributors = [
            contributor["embeds"]["users"]["data"]["attributes"]["full_name"]
            for contributor in r.json()["data"]
        ]
        return contributors

    def _get_license(self, link):
        r = self._get_request_with_bearer_token(link)
        return r.json()["data"]["attributes"]["name"]

    def _get_components(self, link):
        r = self._get_request_with_bearer_token(link)
        return r.json()["data"]

    def _get_institutions(self, link):
        r = self._get_request_with_bearer_token(link)
        if r.json()["data"]:
            institutions = [
                institution["attributes"]["name"] for institution in r.json()["data"]
            ]
            return institutions

    def _get_identifier(self, link):
        r = self._get_request_with_bearer_token(link)
        return r.json()["data"][0]["attributes"]["value"] if r.json()["data"] else False

    def get_all_dataset_description(self):
        osf_dois = []
        datasets = self._query_osf()
        for dataset in datasets:
            # skip datasets that have a parent since the files' components will
            # go into the parent dataset.
            if "parent" in dataset["relationships"].keys():
                continue

            attributes = dataset["attributes"]

            # Retrieve keywords/tags
            keywords = list(map(lambda x: {"value": x}, attributes["tags"]))

            # Retrieve contributors/creators
            contributors = self._get_contributors(
                dataset["relationships"]["contributors"]["links"]["related"]["href"],
            )

            # Retrieve license
            license_ = "None"
            if "license" in dataset["relationships"].keys():
                license_ = self._get_license(
                    dataset["relationships"]["license"]["links"]["related"]["href"],
                )

            # Retrieve institution information
            institutions = self._get_institutions(
                dataset["relationships"]["affiliated_institutions"]["links"]["related"][
                    "href"
                ],
            )

            # Retrieve identifier information
            identifier = self._get_identifier(
                dataset["relationships"]["identifiers"]["links"]["related"]["href"],
            )

            # Get link for the dataset files
            files_link = dataset["relationships"]["files"]["links"]["related"]["href"]

            # Get components list
            components_list = self._get_components(
                dataset["relationships"]["children"]["links"]["related"]["href"],
            )

            # Gather extra properties
            extra_properties = [
                {
                    "category": "logo",
                    "values": [
                        {
                            "value": "https://osf.io/static/img/institutions/shields/cos-shield.png",
                        },
                    ],
                },
            ]
            if institutions:
                extra_properties.append(
                    {
                        "category": "origin_institution",
                        "values": list(
                            map(lambda x: {"value": x}, institutions),
                        ),
                    },
                )

            # Retrieve dates
            date_created = datetime.datetime.strptime(
                attributes["date_created"],
                "%Y-%m-%dT%H:%M:%S.%f",
            )
            date_modified = datetime.datetime.strptime(
                attributes["date_modified"],
                "%Y-%m-%dT%H:%M:%S.%f",
            )

            dataset_dats_content = {
                "title": attributes["title"],
                "files": files_link,
                "components_list": components_list,
                "homepage": dataset["links"]["html"],
                "creators": list(
                    map(lambda x: {"name": x}, contributors),
                ),
                "description": attributes["description"],
                "version": attributes["date_modified"],
                "licenses": [
                    {
                        "name": license_,
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
                "keywords": keywords,
                "distributions": [
                    {
                        "size": 0,
                        "unit": {"value": "B"},
                        "access": {
                            "landingPage": dataset["links"]["html"],
                            "authorizations": [
                                {
                                    "value": "public"
                                    if attributes["public"]
                                    else "private",
                                },
                            ],
                        },
                    },
                ],
                "extraProperties": extra_properties,
            }

            if identifier:
                source = "OSF DOI" if "OSF.IO" in identifier else "DOI"
                dataset_dats_content["identifier"] = {
                    "identifier": identifier,
                    "identifierSource": source,
                }

            osf_dois.append(dataset_dats_content)

        if self.verbose:
            print("Retrieved OSF DOIs: ")
            for osf_doi in osf_dois:
                print(
                    "- Title: {}, Last modified: {}".format(
                        osf_doi["title"],
                        osf_doi["version"],
                    ),
                )

        return osf_dois

    def add_new_dataset(self, dataset: Dict[str, Any], dataset_dir: str):
        d: Dataset = self.datalad.Dataset(dataset_dir)
        d.no_annex(".conp-osf-crawler.json")
        d.save()
        annex: Callable = Repo(dataset_dir).git.annex
        dataset_size: List[int] = []

        # Setup private OSF dataset if the dataset is private
        is_private: bool = self._setup_private_dataset(
            dataset["files"],
            dataset_dir,
            annex,
            d,
        )
        self._download_files(
            dataset["files"],
            dataset_dir,
            "",
            d,
            annex,
            dataset_size,
            is_private,
        )
        if dataset["components_list"]:
            self._download_components(
                dataset["components_list"],
                dataset_dir,
                "",
                d,
                annex,
                dataset_size,
                is_private,
            )
        dataset_size_num, dataset_unit = humanize.naturalsize(sum(dataset_size)).split(
            " ",
        )
        dataset["distributions"][0]["size"] = float(dataset_size_num)
        dataset["distributions"][0]["unit"]["value"] = dataset_unit

        # Add .conp-osf-crawler.json tracker file
        _create_osf_tracker(
            os.path.join(dataset_dir, ".conp-osf-crawler.json"),
            dataset,
        )

    def update_if_necessary(self, dataset_description, dataset_dir):
        tracker_path = os.path.join(dataset_dir, ".conp-osf-crawler.json")
        if not os.path.isfile(tracker_path):
            print("{} does not exist in dataset, skipping".format(tracker_path))
            return False
        with open(tracker_path) as f:
            tracker = json.load(f)
        if tracker["version"] == dataset_description["version"]:
            # Same version, no need to update
            if self.verbose:
                print(
                    "{}, version {} same as OSF version DOI, no need to update".format(
                        dataset_description["title"],
                        dataset_description["version"],
                    ),
                )
            return False
        else:
            # Update dataset
            if self.verbose:
                print(
                    "{}, version {} different from OSF version DOI {}, updating".format(
                        dataset_description["title"],
                        tracker["version"],
                        dataset_description["version"],
                    ),
                )

            # Remove all data and DATS.json files
            for file_name in os.listdir(dataset_dir):
                if file_name[0] == ".":
                    continue
                self.datalad.remove(os.path.join(dataset_dir, file_name), check=False)

            d = self.datalad.Dataset(dataset_dir)
            annex = Repo(dataset_dir).git.annex

            dataset_size = []
            is_private: bool = self._is_private_dataset(dataset_description["files"])
            self._download_files(
                dataset_description["files"],
                dataset_dir,
                "",
                d,
                annex,
                dataset_size,
                is_private,
            )
            if dataset_description["components_list"]:
                self._download_components(
                    dataset_description["components_list"],
                    dataset_dir,
                    "",
                    d,
                    annex,
                    dataset_size,
                )
            dataset_size, dataset_unit = humanize.naturalsize(sum(dataset_size)).split(
                " ",
            )
            dataset_description["distributions"][0]["size"] = float(dataset_size)
            dataset_description["distributions"][0]["unit"]["value"] = dataset_unit

            # Add .conp-osf-crawler.json tracker file
            _create_osf_tracker(
                os.path.join(dataset_dir, ".conp-osf-crawler.json"),
                dataset_description,
            )

            return True

    def get_readme_content(self, dataset):
        readme_content = """# {}

Crawled from [OSF]({})

## Description

{}""".format(
            dataset["title"],
            dataset["homepage"],
            dataset["description"],
        )

        if "identifier" in dataset:
            readme_content += """

DOI: {}""".format(
                dataset["identifier"]["identifier"],
            )

        return readme_content

    def _setup_private_dataset(
        self,
        files_url: str,
        dataset_dir: str,
        annex: Callable,
        dataset: Dataset,
    ) -> bool:
        # Check if the dataset is indeed private
        if self._is_private_dataset(files_url):
            if self.verbose:
                print(
                    "Dataset is private, creating OSF provider and make git annex autoenable datalad remote",
                )

            # Create OSF provider file and needed directories and don't annex the file
            datalad_dir: str = os.path.join(dataset_dir, ".datalad")
            if not os.path.exists(datalad_dir):
                os.mkdir(datalad_dir)
            providers_dir: str = os.path.join(datalad_dir, "providers")
            if not os.path.exists(providers_dir):
                os.mkdir(providers_dir)
            osf_config_path: str = os.path.join(providers_dir, "OSF.cfg")
            with open(osf_config_path, "w") as f:
                f.write(
                    """[provider:OSF]
url_re = .*osf\\.io.*
authentication_type = bearer_token
credential = OSF

[credential:OSF]
# If known, specify URL or email to how/where to request credentials
# url = ???
type = token"""
                )
            dataset.no_annex(os.path.join("**", "OSF.cfg"))

            # Make git annex autoenable datalad remote
            annex(
                "initremote",
                "datalad",
                "externaltype=datalad",
                "type=external",
                "encryption=none",
                "autoenable=true",
            )

            # Set OSF token as a environment variable for authentication
            os.environ["DATALAD_OSF_token"] = self.osf_token

            # Save changes
            dataset.save()

            return True

        return False

    def _is_private_dataset(self, files_url) -> bool:
        return True if requests.get(files_url).status_code == 401 else False
