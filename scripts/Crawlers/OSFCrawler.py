import datetime
import json
import os
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

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


OSF_ZIP = "https://files.us.osf.io/v1/resources/{}/providers/osfstorage/?zip="
ADDON_NAMES = {"github": "GitHub", "gitlab": "GitLab", "bitbucket": "Bitbucket"}


def _size_and_unit(num_bytes):
    """humanize.naturalsize, with the unit spellings DATS records use
    ("kB" -> "KB", "Bytes" -> "B")."""
    size, unit = humanize.naturalsize(num_bytes or 0).split(" ")
    unit = {"kB": "KB", "Bytes": "B", "Byte": "B"}.get(unit, unit)
    return float(size), unit


def build_download_distributions(base, parts, total_size, total_unit, landing, public):
    """DATS distributions for an OSF record, one per downloadable part.

    ``base`` is the crawler's single distribution (landingPage,
    authorizations, formats...). ``parts`` lists where the files are, in
    order: {"kind": "osfstorage" or an add-on provider, "node", "title",
    "bytes", "root", "archive"} ("archive" = a download address for add-on
    code, e.g. a GitHub archive; None when there is none).

    - all files in the project's own storage: one distribution, with
      accessURL = OSF's zip of that storage (empty "zip=": OSF ignores its
      value, which is how "…/znt9d/…?zip=<other id>" served the wrong data);
    - files in components or add-ons: one distribution per part, with a
      title, its own size, the component as identifier and its own zip; an
      add-on part gets its repository's archive, or no accessURL;
    - private records: no accessURL (OSF needs a sign-in).
    Sizes of the parts add up to the record's size.
    """
    parts = [p for p in parts if p.get("bytes") or p.get("files")]
    single = len(parts) == 1 and parts[0]["kind"] == "osfstorage" and parts[0].get("root")
    if single or not parts:
        dist = json.loads(json.dumps(base))
        dist["size"] = total_size
        dist["unit"] = {"value": total_unit}
        if public and parts:
            dist.setdefault("access", {})["accessURL"] = OSF_ZIP.format(parts[0]["node"])
        return [dist]

    distributions = []
    for part in parts:
        dist = json.loads(json.dumps(base))
        size, unit = _size_and_unit(part.get("bytes"))
        dist["size"] = size
        dist["unit"] = {"value": unit}
        access = dist.setdefault("access", {})
        access["landingPage"] = landing
        access.pop("accessURL", None)
        if part["kind"] == "osfstorage":
            dist["title"] = "Main project files" if part.get("root") else part["title"]
            if not part.get("root"):
                dist["identifier"] = {
                    "identifier": f"https://osf.io/{part['node']}/",
                    "identifierSource": "OSF",
                }
            if public:
                access["accessURL"] = OSF_ZIP.format(part["node"])
        else:
            host = ADDON_NAMES.get(part["kind"], part["kind"].capitalize())
            code = f"code ({host}: {part.get('repo') or part['kind']})"
            dist["title"] = "C" + code[1:] if part.get("root") else f"{part['title']}: {code}"
            if part.get("repo_url"):
                dist["identifier"] = {"identifier": part["repo_url"], "identifierSource": host}
            elif not part.get("root"):
                dist["identifier"] = {
                    "identifier": f"https://osf.io/{part['node']}/",
                    "identifierSource": "OSF",
                }
            if public and part.get("archive"):
                access["accessURL"] = part["archive"]
        distributions.append(dist)
    return distributions


class OSFCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force, no_pr, basedir):
        super().__init__(github_token, config_path, verbose, force, no_pr, basedir)
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
                    filename = file["attributes"]["name"]
                    url = file["links"]["download"]

                    # Handle zip files: only register URL, don't download
                    if filename.endswith(".zip"):
                        target_path = os.path.join(inner_path, filename)
                        if self.verbose:
                            print("Registering zip (no download):", target_path)
                        annex("addurl", "--fast", url, "--file", target_path)
                    else:
                        d.download_url(
                            url,
                            path=os.path.join(inner_path, ""),
                            archive=False,
                        )

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

    def _list_osf_files(self, link):
        """(number of files, bytes) under an OSF files link, recursively."""
        count, size = 0, 0
        while link:
            r_json = self._get_request_with_bearer_token(link).json()
            for item in r_json["data"]:
                attributes = item["attributes"]
                if attributes["kind"] == "file":
                    count += 1
                    size += attributes.get("size") or 0
                else:
                    sub_count, sub_size = self._list_osf_files(
                        item["relationships"]["files"]["links"]["related"]["href"],
                    )
                    count += sub_count
                    size += sub_size
            link = (r_json.get("links") or {}).get("next")
        return count, size

    def _github_archive(self, folder_id):
        """("owner/repo", repository URL, archive URL, size in bytes) for an
        OSF GitHub add-on whose folder_id is "owner/repo:" or "owner/repo:branch"."""
        repo, _, branch = str(folder_id or "").partition(":")
        repo = repo.replace("%2F", "/")
        if not repo:
            return None, None, None, 0
        r = requests.get(f"https://api.github.com/repos/{repo}", timeout=30)
        info = r.json() if r.ok else {}
        branch = branch or info.get("default_branch")
        url = f"https://github.com/{repo}"
        archive = f"{url}/archive/refs/heads/{branch}.zip" if branch else None
        # OSF lists add-on files without sizes; GitHub gives the repository's (in KB)
        return repo, url, archive, int(info.get("size") or 0) * 1024

    def _osf_parts(self, node, title, root=True):
        """Where an OSF project's files are: its own storage, each add-on
        (GitHub, GitLab...) and each component, recursively."""
        parts = []
        providers = self._get_request_with_bearer_token(
            f"https://api.osf.io/v2/nodes/{node}/files/",
        ).json()["data"]
        for provider in providers:
            name = provider["attributes"].get("provider") or provider["attributes"]["name"]
            count, size = self._list_osf_files(
                provider["relationships"]["files"]["links"]["related"]["href"],
            )
            if not count:
                continue
            part = {"kind": name, "node": node, "title": title, "root": root,
                    "files": count, "bytes": size}
            if name != "osfstorage":
                addon = self._get_request_with_bearer_token(
                    f"https://api.osf.io/v2/nodes/{node}/addons/{name}/",
                ).json()["data"]["attributes"]
                if name == "github":
                    part["repo"], part["repo_url"], part["archive"], github_size = self._github_archive(
                        addon.get("folder_id"),
                    )
                    part["bytes"] = part["bytes"] or github_size
                else:
                    part["repo"] = str(addon.get("folder_id") or "").replace("%2F", "/").rstrip(":")
            parts.append(part)
        for component in self._get_components(
            f"https://api.osf.io/v2/nodes/{node}/children/",
        ):
            parts += self._osf_parts(component["id"], component["attributes"]["title"], False)
        return parts

    def _set_download_distributions(self, dataset, size, unit, is_private):
        base = dataset["distributions"][0]
        try:
            parts = self._osf_parts(dataset["osf_node_id"], dataset["title"])
        except Exception as e:  # never block a crawl on the download links
            print(f'Could not list the OSF parts of {dataset["title"]}: {e}')
            parts = []
        dataset["distributions"] = build_download_distributions(
            base, parts, float(size), unit, base.get("access", {}).get("landingPage"),
            public=not is_private,
        )

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

    def _get_wiki(self, link) -> Optional[str]:
        r = self._get_request_with_bearer_token(link)
        data = r.json()["data"]
        if len(data) > 0:
            return self._get_request_with_bearer_token(
                data[0]["links"]["download"]
            ).content.decode()

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

            # Get wiki to put in README
            wiki: Optional[str] = None
            try:
                wiki = self._get_wiki(
                    dataset["relationships"]["wikis"]["links"]["related"]["href"]
                )
            except Exception as e:
                print(f'Error getting wiki for {attributes["title"]} because of {e}')

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
                "osf_node_id": dataset["id"],
                "title": attributes["title"],
                "files": files_link,
                "components_list": components_list,
                "homepage": dataset["links"]["html"],
                "creators": list(
                    map(lambda x: {"name": x}, contributors),
                ),
                "description": attributes["description"],
                "wiki": wiki,
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
        self._set_download_distributions(dataset, dataset_size_num, dataset_unit, is_private)

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
                    "{}, version {} same as OSF version DOI ({}), no need to update".format(
                        dataset_description["title"],
                        dataset_description["version"],
                        tracker["version"],
                    ),
                )
            return False

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
                is_private,
            )
        dataset_size, dataset_unit = humanize.naturalsize(sum(dataset_size)).split(
            " ",
        )
        dataset_description["distributions"][0]["size"] = float(dataset_size)
        dataset_description["distributions"][0]["unit"]["value"] = dataset_unit
        self._set_download_distributions(
            dataset_description, dataset_size, dataset_unit, is_private,
        )

        # Add .conp-osf-crawler.json tracker file
        _create_osf_tracker(
            os.path.join(dataset_dir, ".conp-osf-crawler.json"),
            dataset_description,
        )

        return True

    def get_readme_content(self, dataset):
        readme_content = (
            f'# {dataset["title"]}\n\nCrawled from [OSF]({dataset["homepage"]})'
        )

        if "description" in dataset and dataset["description"]:
            readme_content += f'\n\n## Description\n\n{dataset["description"]}'

        if "identifier" in dataset and dataset["identifier"]:
            readme_content += f'\n\n## DOI: {dataset["identifier"]["identifier"]}'

        if "wiki" in dataset and dataset["wiki"]:
            readme_content += f'\n\n## WIKI\n\n{dataset["wiki"]}'

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
