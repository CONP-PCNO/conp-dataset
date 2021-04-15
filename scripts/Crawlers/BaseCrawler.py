import abc
import json
import os
import re

import git
import requests
from datalad import api


class BaseCrawler:
    """
    Interface to extend conp-dataset crawlers.

    ==================
    Overview
    ==================

    Any crawler created from this interface will have to crawl
    datasets from a specific remote platforms. This base class
    implements the functions common to all crawled backends, in particular:
    (1) verify that correct fork of conp-dataset is used,
    (2) create and switch to an new branch for each new dataset,
    (3) ignore README and DATS files for the annex,
    (4) create new datalad datasets,
    (5) publish to GitHub repository,
    (6) create pull requests.

    Method run(), implemented in the base class, is the entry point to any crawler.
    It does the following things:
    (1) It calls abstract method get_all_dataset_description(), that must be implemented
    by the crawler in the child class. get_all_dataset_description()
    retrieves from the remote platform
    all the necessary information about each dataset that is supposed to be added or
    updated to conp-dataset.
    (2) It iterates through each dataset description, and switch to a dedicated git branch
    for each dataset.
       (2.a) If the dataset is new, the base class will create a new branch,
             an empty datalad repository, unannex DATS.json and README.md and create an
             empty GitHub repository. It will then call abstract method add_new_dataset()
             which will add/download all dataset files under given directory.
             The crawler will then add a custom DATS.json and README.md if those weren't added.
             Creating the README.md requires get_readme_content() to be implemented, which will
             return the content of the README.md in markdown format. The crawler will then save and
             publish all changes to the newly create repository. It will also handle adding a new submodule
             to .gitmodules and creating a pull request to CONP-PCNO/conp-dataset.
       (2.b) If the dataset already exists, verified by the existence of its corresponding branch,
             the base class will call abstract method update_if_necessary() which will verify
             if the dataset requires updating and update if so. If the dataset got updated, This method
             will return True which will trigger saving, publishing new content to the dataset's respective
             repository, creating a new DATS.json if it doesn't exist and creating a pull
             request to CONP-PCNO/conp-dataset.

    ==================
    How to implement a new crawler
    ==================

        (1) Create a class deriving from BaseCrawler
        (2) Implement the four abstract methods:
            * get_all_dataset_description,
            * add_new_dataset
            * update_if_necessary
            * get_readme_content.
            See docstrings of each method for specifications.
        (3) In crawl.py, locate the comment where it says to instantiate new crawlers,
            instantiate this new Crawler and call run() on it
    """

    def __init__(self, github_token, config_path, verbose, force, no_pr):
        self.repo = git.Repo()
        self.username = self._check_requirements()
        self.github_token = github_token
        self.config_path = config_path
        self.verbose = verbose
        self.force = force
        self.git = git
        self.datalad = api
        self.no_pr = no_pr

    @abc.abstractmethod
    def get_all_dataset_description(self):
        """
        Get relevant datasets' description from platform.

        Retrieves datasets' description that needs to be in CONP-datasets
        from platform specific to each crawler like Zenodo, OSF, etc. It is up
        to the crawler to identify which datasets on the platform should be crawled.
        The Zenodo crawler uses keywords for this purpose, but other mechanisms
        could work too.

        Each description is required to have the necessary information in order
        to build a valid DATS file from it. The following keys are necessary in
        each description:
            description["title"]: The name of the dataset, usually one sentence or short description of the dataset
            description["identifier"]: The identifier of the dataset
            description["creators"]: The person(s) or organization(s) which contributed to the creation of the dataset
            description["description"]: A textual narrative comprised of one or more statements describing the dataset
            description["version"]: A release point for the dataset when applicable
            description["licenses"]: The terms of use of the dataset
            description["keywords"]: Tags associated with the dataset, which will help in its discovery
            description["types"]: A term, ideally from a controlled terminology, identifying the dataset type or nature
                                  of the data, placing it in a typology
        More fields can be added as long as they comply with the DATS schema available at
        https://github.com/CONP-PCNO/schema/blob/master/dataset_schema.json

        Any fields/keys not in the schema will be ignored when creating the dataset's DATS.
        It is fine to add more helpful information for other methods which will use them.

        Here are some examples of valid DATS.json files:
        https://github.com/conp-bot/conp-dataset-Learning_Naturalistic_Structure__Processed_fMRI_dataset/blob/476a1ee3c4df59aca471499b2e492a65bd389a88/DATS.json
        https://github.com/conp-bot/conp-dataset-MRI_and_unbiased_averages_of_wild_muskrats__Ondatra_zibethicus__and_red_squirrels__Tami/blob/c9e9683fbfec71f44a5fc3576515011f6cd024fe/DATS.json
        https://github.com/conp-bot/conp-dataset-PERFORM_Dataset__one_control_subject/blob/0b1e271fb4dcc03f9d15f694cc3dfae5c7c2d358/DATS.json

        Returns:
            List of description of relevant datasets. Each description is a
            dictionary. For example:

            [{
                "title": "PERFORM Dataset Example",
                "description": "PERFORM dataset description",
                "version": "0.0.1",
                ...
             },
             {
                "title": "SIMON dataset example",
                "description: "SIMON dataset description",
                "version": "1.4.2",
                ...
             },
             ...
            ]
        """
        return []

    @abc.abstractmethod
    def add_new_dataset(self, dataset_description, dataset_dir):
        """
        Configure and add newly created dataset to the local CONP git repository.

        The BaseCrawler will take care of a few overhead tasks before
        add_new_dataset() is called, namely:
        (1) Creating and checkout a dedicated branch for this dataset
        (2) Initialising a Github repo for this dataset
        (3) Creating an empty datalad dataset for files to be added
        (4) Annex ignoring README.md and DATS.json

        After add_new_dataset() is called, BaseCrawler will:
        (1) Create a custom DATS.json if it isn't added in add_new_dataset()
        (2) Create a custom README.md with get_readme_content() if that file is non-existent
        (3) Save and publish all changes
        (4) Adding this dataset as a submodule
        (5) Creating a pull request to CONP-PCNO/conp-dataset
        (6) Switch back to the master branch

        This means that add_new_dataset() will only have to implement a few tasks in the given
        previously initialized datalad dataset directory:
        (1) Adding any one time configuration such as annex ignoring files or adding dataset version tracker
        (2) Downloading and unarchiving relevant archives using datalad.download_url(link, archive=True)
        (3) Adding file links as symlinks using annex("addurl", link, "--fast", "--file", filename)

        There is no need to save/push/publish/create pull request
        as those will be done after this function has finished

        Parameter:
        dataset_description (dict): Dictionary containing information on
                                    retrieved dataset from platform. Element of
                                    the list returned by get_all_dataset_description.
        dataset_dir (str): Local directory path where the newly
                           created datalad dataset is located.
        """
        return

    @abc.abstractmethod
    def update_if_necessary(self, dataset_description, dataset_dir):
        """
        Update dataset if it has been modified on the remote platform.

        Determines if local dataset identified by 'identifier'
        needs to be updated. If so, update dataset.

        Similarily to add_new_dataset(), update_if_necessary() will need to
        take care of updating the dataset if required:
        (1) Downloading and unarchiving relevant archives using datalad.download_url(link, archive=True)
        (2) Adding new file links as symlinks using annex("addurl", link, "--fast", "--file", filename)
        (3) Updating any tracker files used to determine if the dataset needs to be updated

        There is no need to save/push/publish/create pull request
        as those will be done after this function has finished

        Parameter:
        dataset_description (dict): Dictionary containing information on
                                    retrieved dataset from platform.
                                    Element of the list returned by
                                    get_all_dataset_description.
        dataset_dir (str): Directory path of the
                           previously created datalad dataset

        Returns:
        bool: True if dataset got modified, False otherwise
        """
        return False

    @abc.abstractmethod
    def get_readme_content(self, dataset_description):
        """
        Returns the content of the README.md in markdown.

        Given the dataset description provided by
        get_all_dataset_description(), return the content of the
        README.md in markdown.

        Parameter:
        dataset_description (dict): Dictionary containing information on
                                    retrieved dataset from platform.
                                    Element of the list returned by
                                    get_all_dataset_description.

        Returns:
        string: Content of the README.md
        """
        return ""

    def run(self):
        """
        DO NOT OVERRIDE THIS METHOD
        This method is the entry point for all Crawler classes.
        It will loop through dataset descriptions collected from get_all_dataset_description(),
        verify if each of those dataset present locally, create a new dataset with add_new_dataset()
        if not. If dataset is already existing locally, verify if dataset needs updating
        with update_if_necessary() and update if so
        """
        dataset_description_list = self.get_all_dataset_description()
        for dataset_description in dataset_description_list:
            clean_title = self._clean_dataset_title(dataset_description["title"])
            branch_name = "conp-bot/" + clean_title
            dataset_dir = os.path.join("projects", clean_title)
            d = self.datalad.Dataset(dataset_dir)
            # Add github token to individual dataset remote urls
            try:
                origin = git.Repo(dataset_dir).remote("origin")
                origin_url = next(origin.urls)
                if "@" not in origin_url:
                    origin.set_url(
                        origin_url.replace(
                            "https://",
                            "https://" + self.github_token + "@",
                        ),
                    )
            except git.exc.NoSuchPathError:
                pass
            if branch_name not in self.repo.remotes.origin.refs:  # New dataset
                self.repo.git.checkout("-b", branch_name)
                repo_title = ("conp-dataset-" + dataset_description["title"])[0:100]
                d.create()
                r = d.create_sibling_github(
                    repo_title,
                    name="origin",
                    github_login=self.github_token,
                    github_passwd=self.github_token,
                )
                self._add_github_repo_description(repo_title, dataset_description)
                d.no_annex("DATS.json")
                d.no_annex("README.md")
                self.add_new_dataset(dataset_description, dataset_dir)
                # Create DATS.json if it doesn't exist
                if not os.path.isfile(os.path.join(dataset_dir, "DATS.json")):
                    self._create_new_dats(
                        dataset_dir,
                        os.path.join(dataset_dir, "DATS.json"),
                        dataset_description,
                    )
                # Create README.md if it doesn't exist
                if not os.path.isfile(os.path.join(dataset_dir, "README.md")):
                    readme = self.get_readme_content(dataset_description)
                    self._create_readme(readme, os.path.join(dataset_dir, "README.md"))
                d.save()
                d.publish(to="origin")
                self.repo.git.submodule(
                    "add",
                    r[0][1].replace(self.github_token + "@", ""),
                    dataset_dir,
                )
                modified = True
                commit_msg = "Created " + dataset_description["title"]
            else:  # Dataset already existing locally
                self.repo.git.checkout("-f", branch_name)
                try:
                    self.repo.git.merge("-n", "--no-verify", "master")
                except Exception as e:
                    print(f"Error while merging master into {branch_name}: {e}")
                    print("Skipping this dataset")
                    self.repo.git.checkout("master")
                    continue

                modified = self.update_if_necessary(dataset_description, dataset_dir)
                if modified:
                    # Create DATS.json if it doesn't exist
                    if not os.path.isfile(os.path.join(dataset_dir, "DATS.json")):
                        self._create_new_dats(
                            dataset_dir,
                            os.path.join(dataset_dir, "DATS.json"),
                            dataset_description,
                        )
                    # Create README.md if it doesn't exist
                    if not os.path.isfile(os.path.join(dataset_dir, "README.md")):
                        readme = self.get_readme_content(dataset_description)
                        self._create_readme(
                            readme,
                            os.path.join(dataset_dir, "README.md"),
                        )
                    d.save()
                    d.publish(to="origin")
                commit_msg = "Updated " + dataset_description["title"]

            # If modification detected in dataset, push to branch and create PR
            if modified:
                self._push_and_pull_request(
                    commit_msg,
                    dataset_dir,
                    dataset_description["title"],
                )

            # Go back to master
            self.repo.git.checkout("master")

    def _add_github_repo_description(self, repo_title, dataset_description):
        url = "https://api.github.com/repos/{}/{}".format(
            self.username,
            repo_title,
        )
        head = {"Authorization": "token {}".format(self.github_token)}
        description = "Please don't submit any PR to this repository. "
        if "creators" in dataset_description.keys():
            description += (
                "If you want to request modifications, please contact "
                f"{dataset_description['creators'][0]['name']}"
            )
        payload = {"description": description}
        r = requests.patch(url, data=json.dumps(payload), headers=head)
        if not r.ok:
            print(
                "Problem adding description to repository {}:".format(repo_title),
            )
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
        clean_title = self._clean_dataset_title(title)
        origin = self.repo.remote("origin")
        origin_url = next(origin.urls)
        if "@" not in origin_url:
            origin.set_url(
                origin_url.replace("https://", "https://" + self.github_token + "@"),
            )
        self.repo.git.push("--set-upstream", "origin", "conp-bot/" + clean_title)

        # Create PR
        print("Creating PR for " + title)
        if not self.no_pr:
            r = requests.post(
                "https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls",
                json={
                    "title": "Crawler result ({})".format(title),
                    "body": """## Description
{}

## Checklist

Mandatory files and elements:
- [x] A `README.md` file, at the root of the dataset
- [x] A `DATS.json` file, at the root of the dataset
- [ ] If configuration is required (for instance to enable a special remote),
 a `config.sh` script at the root of the dataset
- [x] A DOI (see instructions in [contribution guide]
(https://github.com/CONP-PCNO/conp-dataset/blob/master/.github/CONTRIBUTING.md), and corresponding badge in `README.md`

Functional checks:
- [x] Dataset can be installed using DataLad, recursively if it has sub-datasets
- [x] Every data file has a URL
- [x] Every data file can be retrieved or requires authentication
- [ ] `DATS.json` is a valid DATs model
- [ ] If dataset is derived data, raw data is a sub-dataset
""".format(
                        msg + "\n",
                    ),
                    "head": self.username + ":conp-bot/" + clean_title,
                    "base": "master",
                },
                headers={"Authorization": "token {}".format(self.github_token)},
            )
            if r.status_code != 201:
                raise Exception("Error while creating pull request: " + r.text)

    def _clean_dataset_title(self, title):
        return re.sub(r"\W|^(?=\d)", "_", title)

    def _create_new_dats(self, dataset_dir, dats_path, dataset):
        # Fields/properties that are acceptable in DATS schema according to
        # https://github.com/CONP-PCNO/schema/blob/master/dataset_schema.json
        dats_fields = [
            "title",
            "identifier",
            "creators",
            "description",
            "version",
            "licenses",
            "keywords",
            "distributions",
            "extraProperties",
            "alternateIdentifiers",
            "relatedIdentifiers",
            "dates",
            "storedIn",
            "spatialCoverage",
            "types",
            "availability",
            "refinement",
            "aggregation",
            "privacy",
            "dimensions",
            "primaryPublications",
            "citations",
            "citationCount",
            "producedBy",
            "isAbout",
            "hasPart",
            "acknowledges",
        ]

        # Check required properties
        required_fields = [
            "title",
            "types",
            "creators",
            "licenses",
            "description",
            "keywords",
            "version",
        ]
        for field in required_fields:
            if field not in dataset.keys():
                print(
                    "Warning: required property {} not found in dataset description".format(
                        field,
                    ),
                )

        # Add all dats properties from dataset description
        data = {key: value for key, value in dataset.items() if key in dats_fields}

        # Add file count
        num = 0
        for file in os.listdir(dataset_dir):
            file_path = os.path.join(dataset_dir, file)
            if file[0] == "." or file == "DATS.json" or file == "README.md":
                continue
            elif os.path.isdir(file_path):
                num += sum([len(files) for r, d, files in os.walk(file_path)])
            else:
                num += 1
        if "extraProperties" not in data.keys():
            data["extraProperties"] = [
                {"category": "files", "values": [{"value": str(num)}]},
            ]
        else:
            data["extraProperties"].append(
                {"category": "files", "values": [{"value": str(num)}]},
            )

        # Retrieve modalities from files
        file_paths = map(
            lambda x: x.split(" ")[-1],
            filter(
                lambda x: " " in x,
                git.Repo(dataset_dir).git.annex("list").split("\n"),
            ),
        )  # Get file paths
        file_names = list(
            map(lambda x: x.split("/")[-1] if "/" in x else x, file_paths),
        )  # Get file names from path
        modalities = {self._guess_modality(file_name) for file_name in file_names}
        if len(modalities) == 0:
            modalities.add("unknown")
        elif len(modalities) > 1 and "unknown" in modalities:
            modalities.remove("unknown")
        if "types" not in data.keys():
            data["types"] = [{"value": modality} for modality in modalities]
        else:
            for modality in modalities:
                data["types"].append({"value": modality})

        # Create file
        with open(dats_path, "w") as f:
            json.dump(data, f, indent=4)

    def _guess_modality(self, file_name):
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

    def _create_readme(self, content, path):
        with open(path, "w") as f:
            f.write(content)
