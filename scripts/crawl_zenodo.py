import requests
import os
import json
import argparse
from argparse import RawTextHelpFormatter
import datalad.api as api
from re import sub, search
from git import Repo


def crawl():

    # Patch arguments to get token
    github_token, zenodo_token, verbose, force = parse_args()

    # Check requirements and return github username
    username = check_requirements()

    zenodo_dois = get_zenodo_dois(zenodo_token, verbose)
    conp_dois = get_conp_dois(verbose)
    if verbose:
        print("DOIs found on Zenodo: " + str(zenodo_dois))
        print("DOIs found in CONP dataset: " + str(conp_dois))

    # Verify no duplicates in both lists
    verify_duplicates(zenodo_dois, conp_dois)

    # Commit message and directories to be staged
    commit_msg = []
    stage_dirs = []

    for dataset in zenodo_dois:
        index = next((i for (i, d) in enumerate(conp_dois) if d["concept_doi"] == dataset["concept_doi"]), None)

        # If the zenodo dataset exists in conp datasets
        if index is not None:
            # If the conp dataset version isn't the lastest, update
            if dataset["latest_version"] != conp_dois[index]["version"]:
                update_dataset(dataset, conp_dois[index], github_token)
                commit_msg.append("Updated " + dataset["title"])
                stage_dirs.append(conp_dois[index]["directory"])
        else:
            dataset_path = create_new_dataset(dataset, github_token, force, username)
            if dataset_path != "":
                commit_msg.append("Created " + dataset["title"])
                stage_dirs.append(dataset_path)

    if len(commit_msg) >= 1:
        push_and_pull_request(commit_msg, stage_dirs, github_token)
    else:
        print("No changes detected")


def parse_args():
    parser = argparse.ArgumentParser(
                                     formatter_class=RawTextHelpFormatter,
                                     description=r'''
    CONP Zenodo crawler.
    
    Performs the following steps:
    1. searches for all datasets in Zenodo with the keyword
       'canadian-open-neuroscience-platform',
    2. downloads or updates them locally, 
    3. commits and push to a GitHub account (identified by parameter github_token),
    4. creates a pull request to https://github.com/CONP-PCNO/conp-dataset.

    Requirements:
    * GitHub user must have a fork of https://github.com/CONP-PCNO/conp-dataset
    * Script must be run in the base directory of a local clone of this fork
    * Git remote 'origin' of local Git clone must point to that fork. Warning: this script will 
      push dataset updates to 'origin'.
    * Local Git clone must be set to branch 'master' 
    ''')
    parser.add_argument("github_token", action="store", nargs="?", help="GitHub access token")
    parser.add_argument("zenodo_token", action="store", nargs="?", help="Zenodo access token")
    parser.add_argument("--verbose", action="store_true", help="Print debug information")
    parser.add_argument("--force", action="store_true", help="Force updates")
    args = parser.parse_args()

    # If tokens aren't passed as arguments, check ~/.tokens else store tokens
    token_path = os.path.join(os.path.expanduser('~'), ".tokens")
    github_token = args.github_token
    zenodo_token = args.zenodo_token
    stored_tokens = {}
    # If file does not exist, create an empty one else load existing token
    if not os.path.isfile(token_path):
        with open(token_path, "w") as f:
            json.dump({}, f)
    else:
        with open(token_path, "r") as f:
            stored_tokens = json.load(f)

    if not github_token and "github_token" not in stored_tokens.keys():
        raise Exception("Github token not passed by command line argument nor found in ~/.tokens file, "
                        "please pass your github access token via the command line")
    elif github_token:
        stored_tokens["github_token"] = github_token
    else:
        github_token = stored_tokens["github_token"]

    if not zenodo_token and "zenodo_token" not in stored_tokens.keys():
        raise Exception("Zenodo token not passed by command line argument nor found in ~/.tokens file, "
                        "please pass your zenodo access token via the command line")
    elif zenodo_token:
        stored_tokens["zenodo_token"] = zenodo_token
    else:
        zenodo_token = stored_tokens["zenodo_token"]

    # Store stored_tokens into ~/.tokens
    with open(token_path, "w") as f:
        json.dump(stored_tokens, f, indent=4)

    return github_token, zenodo_token, args.verbose, args.force


def get_conp_dois(verbose=False):
    dats_list = []
    dataset_container_dirs = get_dataset_container_dirs()

    for dataset_container in dataset_container_dirs:
        for dataset in os.listdir(dataset_container):
            if dataset[0] == ".":
                continue
            dir_list = os.listdir(os.path.join(dataset_container, dataset))
            dats_name = ""
            if "DATS.json" in dir_list:
                dats_name = "DATS.json"
            if dats_name is not "":
                directory = os.path.join(dataset_container, dataset)
                with open(os.path.join(directory, dats_name), "r") as f:
                    try:
                        dat = json.load(f)
                    except Exception as e:
                        print(("Error while loading DATS file {}: {}. " + 
                               "Dataset will be ignored.").format(f.name, e))
                        continue
                    if "zenodo" in dat.keys():
                        new_dict = dat["zenodo"]
                        new_dict.update({"directory": directory})
                        dats_list.append(new_dict)

    return dats_list


def get_dataset_container_dirs():
    return ["projects", "investigators"]


def get_zenodo_dois(token, verbose=False):
    zenodo_dois = []
    datasets = query_zenodo(verbose)
    for dataset in datasets:

        # Retrieve file urls
        files = []
        if "files" not in dataset.keys():
            # This means the Zenodo dataset files are restricted
            if verbose:
                print(dataset["metadata"]["title"] +
                      ": no files found, dataset is probably restricted, using token to retrieve file url")

            # Try to retrieve file urls using the token
            data = requests.get(dataset["links"]["latest"], params={'access_token': token}).json()
            if "files" not in data.keys():
                print("Unable to access files of dataset {} at url {} "
                      "using the current Zenodo token, skipping this dataset"
                      .format(dataset["metadata"]["title"], dataset["links"]["latest"]))
                continue
            else:
                # Append access token to each file url
                for bucket in data["files"]:
                    bucket["links"]["self"] += "?access_token=" + token
                    files.append(bucket)
        else:
            for bucket in dataset["files"]:
                files.append(bucket)

        doi_badge = dataset["conceptdoi"]
        concept_doi = dataset["conceptrecid"]
        title = clean(dataset["metadata"]["title"])
        if len(dataset["metadata"]["relations"]["version"]) != 1:
            raise Exception("Unexpected multiple versions")
        latest_version_doi = dataset["metadata"]["relations"]["version"][0]["last_child"]["pid_value"]

        zenodo_dois.append({
            "concept_doi": concept_doi,
            "latest_version": latest_version_doi,
            "title": title,
            "files": files,
            "doi_badge": doi_badge
        })

    return zenodo_dois


def query_zenodo(verbose=False):
    query = ("https://zenodo.org/api/records/?"
             "type=dataset&"
             "q=keywords:\"canadian-open-neuroscience-platform\"")
    results = requests.get(query).json()["hits"]["hits"]
    if verbose:
        print("Zenodo query: {}".format(query))
    return results


def verify_duplicates(zenodo_dois, conp_dois):
    concept_dois = list(map(lambda x: x["concept_doi"], zenodo_dois))
    if len(concept_dois) != len(set(concept_dois)):
        raise Exception("Concept DOI duplicates exists in zenodo list")
    version_dois = list(map(lambda x: x["latest_version"], zenodo_dois))
    if len(version_dois) != len(set(version_dois)):
        raise Exception("Version DOI duplicates exists in zenodo list")
    titles = list(map(lambda x: x["title"], zenodo_dois))
    if len(titles) != len(set(titles)):
        raise Exception("Title duplicates exists in zenodo list")
    concept_dois = list(map(lambda x: x["concept_doi"], conp_dois))
    if len(concept_dois) != len(set(concept_dois)):
        raise Exception("Concept DOI duplicates exists in conp list")
    version_dois = list(map(lambda x: x["version"], conp_dois))
    if len(version_dois) != len(set(version_dois)):
        raise Exception("Version DOI duplicates exists in conp list")
    directories = list(map(lambda x: x["directory"], conp_dois))
    if len(directories) != len(set(directories)):
        raise Exception("Directory duplicates exists in conp list")


clean = lambda x: sub('\W|^(?=\d)','_', x)


def create_new_dataset(dataset, token, force, username):
    repo_title = ("conp-dataset-" + dataset["title"])[0:100]
    full_repository = "{}/{}".format(username, repo_title)

    # Check for existing github repo with same name
    if not verify_repository(username, full_repository, token, dataset, force):
        return ""

    dataset_dir = os.path.join("projects", dataset["title"])
    d = api.Dataset(dataset_dir)
    d.create()

    r = d.create_sibling_github(repo_title,
                                github_login=token,
                                github_passwd=token)
    update_gitmodules(dataset_dir, r[0][1].replace(token + "@", ""))

    for bucket in dataset["files"]:
        d.download_url(bucket["links"]["self"], archive=True if bucket["type"] == "zip" else False)

    # Update DATS.json or create one if it doesn't exist
    if update_dats(os.path.join(dataset_dir, "DATS.json"), dataset):
        commit_msg = "[conp-bot] Updated DATS.json"
    else:
        create_new_dats(os.path.join(dataset_dir, "DATS.json"), dataset)
        commit_msg = "[conp-bot] Create DATS.json"

    commit_push_file(dataset_dir, "DATS.json", commit_msg, token)

    d.publish(to="github")

    # Create and push README.md if doesn't exist to github repo
    if create_readme(dataset, dataset_dir):
        commit_push_file(dataset_dir, "README.md", "[conp-bot] Create README.md", token)

    return d.path


def update_gitmodules(directory, github_url):
    with open(".gitmodules", "a") as f:
        f.write("""[submodule "{0}"]
  path = {0}
  url = {1}
""".format(directory, github_url))


def update_dats(path, dataset):
    if os.path.isfile(path):
        with open(path, "r") as f:
            data = json.load(f)
        data["zenodo"] = {
            "concept_doi": dataset["concept_doi"],
            "version": dataset["latest_version"]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        return True
    else:
        return False


def create_new_dats(path, dataset):
    with open(path, "w") as f:
        data = {
            "zenodo": {
                "concept_doi": dataset["concept_doi"],
                "version": dataset["latest_version"]
            }
        }
        json.dump(data, f, indent=4)


def update_dataset(zenodo_dataset, conp_dataset, token):
    # To update a dataset, we don't know which files have been updated
    # so we have to remove all existing files and redownload all files
    # fresh from the latest version of that zenodo dataset

    dataset_dir = conp_dataset["directory"]
    for file_name in os.listdir(dataset_dir):
        if file_name[0] == "." or file_name == "DATS.json" or file_name == "README.md":
            continue
        api.remove(os.path.join(dataset_dir, file_name), check=False)

    d = api.Dataset(dataset_dir)

    for bucket in zenodo_dataset["files"]:
        d.download_url(bucket["links"]["self"], archive=True if bucket["type"] == "zip" else False)

    # Update DATS.json
    if update_dats(os.path.join(dataset_dir, "DATS.json"), zenodo_dataset):
        commit_push_file(dataset_dir, "DATS.json", "[conp-bot] Update DATS.json", token)
    else:
        raise Exception("No DATS.json file in existing dataset, aborting")

    d.publish(to="github")


def push_and_pull_request(msg, directories, token):
    repo = Repo()
    for directory in directories:
        repo.git.add(directory)
    repo.git.add(".gitmodules")
    repo.git.commit("-m", "[conp-bot] " + ", ".join(msg))
    origin = repo.remote("origin")
    origin_url = next(origin.urls)
    if "@" not in origin_url:
        origin.set_url(origin_url.replace("https://", "https://" + token + "@"))
    origin.push()
    username = search('github.com[/,:](.*)/conp-dataset.git', origin_url).group(1)
    pr_body = ""
    for change in msg:
        pr_body += "- " + change + "\n"
    r = requests.post("https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls?access_token=" + token, json={
        "title": "Zenodo crawler results",
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
""".format(pr_body),
        "head": username + ":master",
        "base": "master"
    })
    if r.status_code != 201:
        raise Exception("Error while creating pull request: " + r.text)


def create_readme(dataset, path):
    if "README.md" not in os.listdir(path):
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write("""# {0}

[![DOI](https://www.zenodo.org/badge/DOI/{1}.svg)](https://doi.org/{1})

Crawled from Zenodo"""
                    .format(dataset["title"], dataset["doi_badge"]))
        return True
    return False


def check_requirements():
    # GitHub user must have a fork of https://github.com/CONP-PCNO/conp-dataset
    # Script must be run in the base directory of a local clone of this fork
    # Git remote 'origin' of local Git clone must point to that fork
    # Local Git clone must be set to branch 'master'
    repo = Repo()
    git_root = repo.git.rev_parse("--show-toplevel")
    if git_root != os.getcwd():
        raise Exception("Script not ran at the base directory of local clone")
    if "origin" not in repo.remotes:
        raise Exception("Remote 'origin' does not exist in current reposition")
    origin_url = next(repo.remote("origin").urls)
    full_name = search('github.com[/,:](.*).git', origin_url).group(1)
    r = requests.get("http://api.github.com/repos/" + full_name).json()
    if not r["fork"] or r["parent"]["full_name"] != "CONP-PCNO/conp-dataset":
        raise Exception("Current repository not a fork of CONP-PCNO/conp-dataset")
    branch = repo.active_branch.name
    if branch != "master":
        raise Exception("Local git clone active branch not set to 'master'")

    # return username
    return full_name.split("/")[0]


def verify_repository(username, full_repository, token, dataset, force):
    if requests.get("http://api.github.com/repos/{}".format(full_repository)).status_code != 404:
        print("Existing {} repository on github".format(full_repository))
        if force:
            print("--force specified, deleting and creating new github repository")
        else:
            msg = "Would you like to delete it? (Y/n)"
            if prompt(msg).upper() != "Y":
                print("Skipping " + dataset["title"])
                return False
        r = requests.delete("http://api.github.com/repos/{}".format(full_repository), auth=(username, token))
        if not r.ok:
            print("Failed to delete {}, please delete it manually or enable the delete_repo scope for the passed token")
            print("Response: {}".format(str(r.content)))
            return False
    return True


def prompt(msg):
    return input(msg)


def commit_push_file(dataset_dir, file_name, msg, token):
    repo = Repo(dataset_dir)
    repo.git.add(file_name)
    repo.git.commit("-m", msg)
    origin = repo.remote("github")
    origin_url = next(origin.urls)
    if "@" not in origin_url:
        origin.set_url(origin_url.replace("https://", "https://" + token + "@"))
    repo.git.push("--set-upstream", "github", "master")


if __name__ == "__main__":
    crawl()
