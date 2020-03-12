from datalad import api
import git
import os
import re
import requests
import abc
import json


class BaseCrawler:
    def __init__(self, github_token, config_path, verbose, force):
        self.repo = git.Repo()
        self.username = self._check_requirements()
        self.github_token = github_token
        self.config_path = config_path
        self.verbose = verbose
        self.force = force
        self.git = git
        self.datalad = api

    @abc.abstractmethod
    def get_all_dataset_metadata(self):
        """
        Get relevant datasets' metadata from platform.

        Retrieves datasets' metadata that needs to be in CONP-datasets
        from platform specific to each crawler like Zenodo, OSF, etc.

        Returns:
            List of metadata of relevant datasets. Each metadata is a
            dictionary and requires the key "title" to be associated
            with the dataset's title. For example:

            [{
                "title": "PERFORM Dataset Example",
                "creators: ["Joey", "Daniel", "Bob"]
             },
             {
                "title": "SIMON dataset example",
                "version": 1.4.2
             },
             ...
            ]
        """
        return []

    @abc.abstractmethod
    def add_new_dataset(self, metadata, dataset_dir):
        """
        Configure and add newly created dataset.

        This is where newly crawled dataset which are not present locally are
        created. This is where a one time configuration such as modifying
        .gitignore, .gitattribute or no-annex some files can be done.

        Parameter:
        metadata (dict): Dictionary containing metadata on
                         retrieved dataset from platform
        dataset_dir (str): Directory path of where the newly
                           created datalad dataset is located
        """
        return

    @abc.abstractmethod
    def update_if_necessary(self, metadata, dataset_dir):
        """
        Update dataset if needed.

        Determines if local dataset needs to be updated based on
        metadata and updates dataset if that is the case.

        Parameter:
        metadata (dict): Dictionary containing metadata on
                         retrieved dataset from platform
        dataset_dir (str): Directory path of the dataset

        Returns:
        bool: True if dataset got modified, else otherwise
        """
        return False

    # DO NOT OVERRIDE THIS METHOD
    def run(self):
        metadata_list = self.get_all_dataset_metadata()
        for metadata in metadata_list:
            clean_title = self._clean_dataset_title(metadata["title"])
            branch_name = "conp-bot/" + clean_title
            dataset_dir = os.path.join("projects", clean_title)
            d = self.datalad.Dataset(dataset_dir)
            if branch_name not in self.repo.remotes.origin.refs:  # New dataset
                self.repo.git.checkout("-b", branch_name)
                repo_title = ("conp-dataset-" + metadata["title"])[0:100]
                d.create()
                r = d.create_sibling_github(
                    repo_title,
                    name="origin",
                    github_login=self.github_token,
                    github_passwd=self.github_token)
                self._add_github_repo_description(repo_title, metadata)
                d.no_annex("DATS.json")
                d.no_annex("README.md")
                self.add_new_dataset(metadata, dataset_dir)
                d.save()
                d.publish(to="origin")
                self.repo.git.submodule(
                    "add",
                    r[0][1].replace(self.github_token + "@", ""),
                    dataset_dir)
                modified = True
                commit_msg = "Created " + metadata["title"]
            else:  # Dataset already existing locally
                self.repo.git.checkout(branch_name)
                modified = self.update_if_necessary(metadata, dataset_dir)
                if modified:
                    d.save()
                    d.publish(to="origin")
                commit_msg = "Updated " + metadata["title"]

            # If modification detected in dataset, push to branch and create PR
            if modified:
                self._push_and_pull_request(commit_msg, dataset_dir, metadata["title"])

            # Go back to master
            self.repo.git.checkout("master")

    def _add_github_repo_description(self, repo_title, metadata):
        url = "https://api.github.com/repos/{}/{}".format(
            self.username, repo_title)
        head = {"Authorization": "token {}".format(self.github_token)}
        description = "Please don't submit any PR to this repository. "
        if "creators" in metadata.keys():
            description += "If you want to request modifications, " \
                           "please contact {}".format(
                            metadata["creators"][0]["name"])
        payload = {"description": description}
        r = requests.patch(url, data=json.dumps(payload), headers=head)
        if not r.ok:
            print("Problem adding description to repository {}:"
                  .format(repo_title))
            print(r.content)

    def _check_requirements(self):
        # GitHub user must have a fork of https://github.com/CONP-PCNO/conp-dataset
        # Script must be run in the base directory of a local clone of this fork
        # Git remote 'origin' of local Git clone must point to that fork
        # Local Git clone must be set to branch 'master'
        git_root = self.repo.git.rev_parse("--show-toplevel")
        if git_root != os.getcwd():
            raise Exception("Script not ran at the base directory of local clone")
        if "origin" not in self.repo.remotes:
            raise Exception("Remote 'origin' does not exist in current reposition")
        origin_url = next(self.repo.remote("origin").urls)
        full_name = re.search("github.com[/,:](.*).git", origin_url).group(1)
        r = requests.get("http://api.github.com/repos/" + full_name).json()
        if not r["fork"] or r["parent"]["full_name"] != "CONP-PCNO/conp-dataset":
            raise Exception("Current repository not a fork of CONP-PCNO/conp-dataset")
        branch = self.repo.active_branch.name
        if branch != "master":
            raise Exception("Local git clone active branch not set to 'master'")

        # Return username
        return full_name.split("/")[0]

    def _push_and_pull_request(self, msg, dataset_dir, title):
        self.repo.git.add(dataset_dir)
        self.repo.git.add(".gitmodules")
        self.repo.git.commit("-m", "[conp-bot] " + msg)
        origin = self.repo.remote("origin")
        origin_url = next(origin.urls)
        if "@" not in origin_url:
            origin.set_url(origin_url.replace("https://", "https://" + self.github_token + "@"))
        self.repo.git.push("--set-upstream", "origin", "conp-bot/" + title)

        # Create PR
        print("Creating PR for " + title)
        r = requests.post(
            "https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls?access_token="
            + self.github_token,
            json={
                "title": "Crawler result ({})".format(title),
                "body": """## Description
{}

## Checklist

Mandatory files and elements:
- [x] A `README.md` file, at the root of the dataset
- [x] A `DATS.json` file, at the root of the dataset
- [ ] If configuration is required (for instance to enable a special remote), a `config.sh` script at the root of the dataset
- [x] A DOI (see instructions in [contribution guide](https://github.com/CONP-PCNO/conp-dataset/blob/master/.github/CONTRIBUTING.md), and corresponding badge in `README.md`

Functional checks:
- [x] Dataset can be installed using DataLad, recursively if it has sub-datasets
- [x] Every data file has a URL
- [x] Every data file can be retrieved or requires authentication
- [ ] `DATS.json` is a valid DATs model
- [ ] If dataset is derived data, raw data is a sub-dataset
""".format(
                    msg + "\n"
                ),
                "head": self.username + ":conp-bot/" + title,
                "base": "master",
            },
        )
        if r.status_code != 201:
            raise Exception("Error while creating pull request: " + r.text)

    def _clean_dataset_title(self, title):
        return re.sub("\W|^(?=\d)", "_", title)