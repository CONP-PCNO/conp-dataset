from scripts.Crawlers.BaseCrawler import BaseCrawler
from git import Repo
import os
import json
import requests
import humanize
import html2markdown


def _guess_modality(file_name):
    # Associate file types to substrings found in the file name
    modalities = {
        "fMRI": ["bold", "func", "cbv"],
        "MRI": ["T1", "T2", "FLAIR", "FLASH", "PD", "angio", "anat", "mask"],
        "diffusion": ["dwi", "dti", "sbref"],
        "meg": ["meg"],
        "intracranial eeg": ["ieeg"],
        "eeg": ["eeg"],
        "field map": ["fmap", "phasediff", "magnitude"],
        "imaging": ["nii", "nii.gz", "mnc"],
    }
    for m in modalities:
        for s in modalities[m]:
            if s in file_name:
                return m
    return "unknown"


def _get_unlock_script():
    with open(os.path.join("scripts", "unlock.py"), "r") as f:
        return f.read()


def _create_new_dats(dataset_dir, dats_path, dataset):
    with open(dats_path, "w") as f:
        data = {
            "title": dataset["original_title"],
            "identifier": dataset["identifier"],
            "creators": dataset["creators"],
            "description": dataset["description"],
            "version": dataset["version"],
            "licenses": dataset["licenses"],
            "keywords": dataset["keywords"],
            "distributions": dataset["distributions"],
            "extraProperties": dataset["extraProperties"],
        }

        # Count number of files in dataset
        num = 0
        for file in os.listdir(dataset_dir):
            if file[0] == "." or file == "DATS.json" or file == "README.md":
                continue
            elif os.path.isdir(file):
                num += sum(
                    [
                        len(list(filter(lambda x: x[0] != ".", files)))
                        for r, d, files in os.walk(file)
                    ]
                )
            else:
                num += 1
        data["extraProperties"].append(
            {"category": "files", "values": [{"value": str(num)}]}
        )

        # Retrieve modalities from files
        file_paths = map(
            lambda x: x.split(" ")[-1],
            filter(lambda x: " " in x, Repo(dataset_dir).git.annex("list").split("\n")),
        )  # Get file paths
        file_names = list(
            map(lambda x: x.split("/")[-1] if "/" in x else x, file_paths)
        )  # Get file names from path
        modalities = set([_guess_modality(file_name) for file_name in file_names])
        if len(modalities) == 0:
            modalities.add("unknown")
        elif len(modalities) > 1 and "unknown" in modalities:
            modalities.remove("unknown")
        data["types"] = [{"value": modality} for modality in modalities]

        json.dump(data, f, indent=4)


def _create_zenodo_tracker(path, dataset, private_files, restricted):
    with open(path, "w") as f:
        data = {
            "zenodo": {
                "concept_doi": dataset["concept_doi"],
                "version": dataset["latest_version"],
            },
            "private_files": private_files,
            "restricted": restricted,
            "title": dataset["original_title"],
        }
        json.dump(data, f, indent=4)


def _create_readme(dataset, dataset_dir):
    if "README.md" not in os.listdir(dataset_dir):
        with open(os.path.join(dataset_dir, "README.md"), "w") as f:
            f.write(
                """# {0}

[![DOI](https://www.zenodo.org/badge/DOI/{1}.svg)](https://doi.org/{1})

Crawled from Zenodo

## Description

{2}""".format(
                    dataset["title"],
                    dataset["doi_badge"],
                    html2markdown.convert(dataset["description"]).replace(
                        "\n", "<br />"
                    ),
                )
            )


class ZenodoCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force):
        super().__init__(github_token, config_path, verbose, force)
        self.zenodo_tokens = self._get_tokens()
        self.unlock_script = _get_unlock_script()

    def _get_tokens(self):
        if os.path.isfile(self.config_path):
            with open(self.config_path, "r") as f:
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
        results = requests.get(query).json()["hits"]["hits"]
        if self.verbose:
            print("Zenodo query: {}".format(query))
        return results

    def _download_file(self, bucket, d, dataset_dir, private_files):
        link = bucket["links"]["self"]
        repo = self.git.Repo(dataset_dir)
        annex = repo.git.annex
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
                for dir_name, dirs, files in os.walk(dataset_dir):
                    for file_name in files:
                        file_path = os.path.join(dir_name, file_name)
                        if ".git" in file_path:
                            continue
                        with open(file_path, "r") as f:
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
                private_files["files"].append({"name": file_name, "link": tokenless_link})
        d.save()

    def _put_unlock_script(self, dataset_dir):
        with open(os.path.join(dataset_dir, "unlock.py"), "w") as f:
            f.write(self.unlock_script)

    def get_all_dataset_metadata(self):
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
                            "skipping this dataset".format(clean_title)
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
                    print("No available tokens to access files of {}".format(metadata["title"]))
                    continue
            else:
                for bucket in dataset["files"]:
                    files.append(bucket)

            latest_version_doi = metadata["relations"]["version"][0]["last_child"]["pid_value"]

            # Retrieve and clean file formats/extensions
            file_formats = (list(set(map(lambda x: x["type"], files))) if len(files) > 0 else None)
            if "" in file_formats:
                file_formats.remove("")

            # Retrieve and clean file keywords
            keywords = []
            if "keywords" in metadata.keys():
                keywords = list(map(lambda x: {"value": x}, metadata["keywords"]))

            dataset_size, dataset_unit = humanize.naturalsize(
                sum([filename["size"] for filename in files])
            ).split(" ")
            dataset_size = float(dataset_size)

            zenodo_dois.append(
                {
                    "identifier": {
                        "identifier": "https://doi.org/{}".format(dataset["conceptdoi"]),
                        "identifierSource": "DOI",
                    },
                    "concept_doi": dataset["conceptrecid"],
                    "latest_version": latest_version_doi,
                    "title": clean_title,
                    "original_title": metadata["title"],
                    "files": files,
                    "doi_badge": dataset["conceptdoi"],
                    "creators": list(
                        map(lambda x: {"name": x["name"]}, metadata["creators"])
                    ),
                    "description": metadata["description"],
                    "version": metadata["version"]
                    if "version" in metadata.keys()
                    else "None",
                    "licenses": [
                        {
                            "name": metadata["license"]["id"]
                            if "license" in metadata.keys()
                            else "None"
                        }
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
                                        else "private"
                                    }
                                ],
                            },
                        }
                    ],
                    "extraProperties": [
                        {
                            "category": "logo",
                            "values": [
                                {
                                    "value": "https://about.zenodo.org/static/img/logos/zenodo-gradient-round.svg"
                                }
                            ],
                        }
                    ],
                }
            )

        return zenodo_dois

    def add_new_dataset(self, metadata, dataset_dir):
        d = self.datalad.Dataset(dataset_dir)
        d.no_annex(".conp-zenodo-crawler.json")
        d.no_annex("unlock.py")
        d.save()

        private_files = {"archive_links": [], "files": []}
        for bucket in metadata["files"]:
            self._download_file(bucket, d, dataset_dir, private_files)
        restricted_dataset = True if len(private_files["archive_links"]) > 0 or len(
            private_files["files"]) > 0 else False

        # Create DATS.json if it doesn't exist
        if not os.path.isfile(os.path.join(dataset_dir, "DATS.json")):
            _create_new_dats(dataset_dir, os.path.join(dataset_dir, "DATS.json"), metadata)

        # Create README.md if doesn't exist
        if not os.path.isfile(os.path.join(dataset_dir, "README.md")):
            _create_readme(metadata, dataset_dir)

        # If dataset is a restricted dataset, create a script which allows to unlock downloading files in dataset
        if restricted_dataset:
            self._put_unlock_script(dataset_dir)

        # Add .conp-zenodo-crawler.json tracker file
        _create_zenodo_tracker(
            os.path.join(dataset_dir, ".conp-zenodo-crawler.json"), metadata, private_files, restricted_dataset
        )

    def update_if_necessary(self, metadata, dataset_dir):
        tracker_path = os.path.join(dataset_dir, ".conp-zenodo-crawler.json")
        if not os.path.isfile(tracker_path):
            raise Exception("{} does not exist in dataset".format(tracker_path))
        with open(tracker_path, "r") as f:
            tracker = json.load(f)
        if tracker["zenodo"]["version"] == metadata["latest_version"]:
            # Same version, no need to update
            return False
        else:
            # Update dataset
            dats_dir = os.path.join(dataset_dir, "DATS.json")

            # Remove all data and DATS.json files
            for file_name in os.listdir(dataset_dir):
                if file_name[0] == "." or file_name == "README.md":
                    continue
                self.datalad.remove(os.path.join(dataset_dir, file_name), check=False)

            d = self.datalad.Dataset(dataset_dir)

            private_files = {"archive_links": [], "files": []}
            for bucket in metadata["files"]:
                self._download_file(bucket, d, dataset_dir, private_files)
            restricted_dataset = True if len(private_files["archive_links"]) > 0 or len(
                private_files["files"]) > 0 else False

            # If DATS.json isn't in downloaded files, create new DATS.json
            if not os.path.isfile(dats_dir):
                _create_new_dats(dataset_dir, dats_dir, metadata)

            # If dataset is a restricted dataset, create a script which allows to unlock downloading files in dataset
            if restricted_dataset:
                self._put_unlock_script(dataset_dir)

            # Add/update .conp-zenodo-crawler.json tracker file
            _create_zenodo_tracker(tracker_path, metadata, private_files, restricted_dataset)

            return True
