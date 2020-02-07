import requests
import os
import json
import argparse
import traceback
from argparse import RawTextHelpFormatter
import datalad.api as api
from datalad.support.annexrepo import AnnexRepo
from re import sub, search
from git import Repo


def crawl():

    # Patch arguments to get token
    github_token, stored_z_tokens, passed_z_tokens, verbose, force = parse_args()

    # Check requirements and return github username
    repo = Repo()
    username = check_requirements(repo)

    zenodo_dois = get_zenodo_dois(stored_z_tokens, passed_z_tokens, verbose)
    conp_dois = get_conp_dois(zenodo_dois, repo, verbose)
    if verbose:
        print("\n\n******************** Listing DOIs ********************")
        print("Zenodo DOIs: ")
        for zenodo_doi in zenodo_dois:
            print("- Title: {}, Concept DOI: {}, Latest version DOI: {}".format(
                zenodo_doi["original_title"], zenodo_doi["concept_doi"], zenodo_doi["latest_version"]))
        print("CONP DOIs: ")
        for conp_doi in conp_dois:
            print("- Title: {}, Concept DOI: {}, Version DOI: {}".format(
                conp_doi["title"], conp_doi["concept_doi"], conp_doi["version"]))

    for dataset in zenodo_dois:
        index = next((i for (i, d) in enumerate(conp_dois) if d["concept_doi"] == dataset["concept_doi"]), None)

        # If the zenodo dataset exists in conp datasets
        if index is not None:
            # If the conp dataset version isn't the latest, update
            if dataset["latest_version"] != conp_dois[index]["version"]:
                if verbose:
                    print("\n\n******************** Updating dataset {} ********************".format(
                        dataset["original_title"]))

                # Switch branch
                switch_branch(repo, "conp-bot/" + dataset["title"])
                update_dataset(dataset, conp_dois[index], github_token)
                push_and_pull_request("Updated " + dataset["title"], conp_dois[index]["directory"], github_token, dataset["title"], repo)
                switch_branch(repo, "master")  # Return to master branch

        else:
            if verbose:
                print("\n\n******************** Creating dataset {} ********************".format(
                    dataset["original_title"]))

            # Switch branch
            switch_branch(repo, "conp-bot/" + dataset["title"], new=True)
            dataset_path = create_new_dataset(dataset, github_token, force, username)
            if dataset_path != "":
                push_and_pull_request("Created " + dataset["title"], dataset_path, github_token, dataset["title"], repo)
            switch_branch(repo, "master")  # Return to master branch

    print("\n\n******************** Done ********************")


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
    parser.add_argument('-z', nargs='*', help="Zenodo access tokens")
    parser.add_argument("--verbose", action="store_true", help="Print debug information")
    parser.add_argument("--force", action="store_true", help="Force updates")
    args = parser.parse_args()

    # If tokens aren't passed as arguments, check ~/.tokens else store tokens
    token_path = os.path.join(os.path.expanduser('~'), ".tokens")
    github_token = args.github_token
    passed_zenodo_tokens = args.z
    stored_zenodo_tokens = None
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

    if not passed_zenodo_tokens and "zenodo_tokens" not in stored_tokens.keys():
        raise Exception("Zenodo tokens not passed by command line argument nor found in ~/.tokens file, "
                        "please pass your zenodo access tokens via the command line")
    if "zenodo_tokens" in stored_tokens.keys():
        stored_zenodo_tokens = stored_tokens["zenodo_tokens"]

    # Store stored_tokens into ~/.tokens
    with open(token_path, "w") as f:
        json.dump(stored_tokens, f, indent=4)

    return github_token, stored_zenodo_tokens, passed_zenodo_tokens, args.verbose, args.force


def get_conp_dois(zenodo_dois, repo, verbose=False):
    if verbose:
        print("\n\n******************** Retrieving CONP DOIs ********************")

    conp_doi_list = []
    dataset_container = get_dataset_container_dir()
    branches = repo.remotes.origin.refs

    for doi in zenodo_dois:
        if "conp-bot/" + doi["title"] in branches:
            switch_branch(repo, "conp-bot/" + doi["title"])
            dir_path = os.path.join(dataset_container, doi["title"])
            api.install(dir_path)
            dir_list = os.listdir(dir_path)
            if ".conp-zenodo-crawler.json" in dir_list:
                with open(os.path.join(dir_path, ".conp-zenodo-crawler.json"), "r") as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        print(("Error while loading file {}: {}. " +
                               "Dataset will be ignored.").format(f.name, e))
                        continue
                    if "zenodo" in data.keys() and "title" in data.keys():
                        new_dict = data["zenodo"]
                        new_dict.update({"title": data["title"]})
                        new_dict.update({"directory": dir_path})
                        conp_doi_list.append(new_dict)

            switch_branch(repo, "master")  # Return to master branch

    return conp_doi_list


def get_dataset_container_dir():
    return "projects"


def get_zenodo_dois(stored_tokens, passed_tokens, verbose=False):
    if verbose:
        print("\n\n******************** Retrieving ZENODO DOIs ********************")

    zenodo_dois = []
    datasets = query_zenodo(verbose)
    for dataset in datasets:
        metadata = dataset["metadata"]
        title = clean(metadata["title"])

        # Retrieve file urls
        files = []
        if "files" not in dataset.keys():
            # This means the Zenodo dataset files are restricted
            # Try to see if the dataset token is already known in stored tokens
            if stored_tokens is not None and title in stored_tokens.keys():
                data = requests.get(dataset["links"]["latest"], params={'access_token': stored_tokens[title]}).json()
                if "files" not in data.keys():
                    print("Unable to access " + title + " using stored tokens, skipping this dataset")
                    continue
                else:
                    # Append access token to each file url
                    for bucket in data["files"]:
                        bucket["links"]["self"] += "?access_token=" + stored_tokens[title]
                        files.append(bucket)
            else:
                # Try to retrieve file urls using the passed tokens
                if passed_tokens is not None:
                    for token in passed_tokens:
                        data = requests.get(dataset["links"]["latest"], params={'access_token': token}).json()
                        if "files" not in data.keys():
                            continue
                        else:
                            # Append access token to each file url
                            for bucket in data["files"]:
                                bucket["links"]["self"] += "?access_token=" + token
                                files.append(bucket)
                            # And store working token and dataset title
                            if stored_tokens is None:
                                stored_tokens = dict()
                            stored_tokens[title] = token
                            break
                    else:
                        print("Unable to access files of dataset {} at url {} "
                              "using the current Zenodo tokens, skipping this dataset"
                              .format(metadata["title"], dataset["links"]["latest"]))
                        continue
                else:
                    print("No tokens available to access files of dataset"
                          " {} at url {}, skipping this dataset"
                          .format(metadata["title"], dataset["links"]["latest"]))
                    continue
        else:
            for bucket in dataset["files"]:
                files.append(bucket)

        # Store known tokens with their associated datasets
        store(stored_tokens)

        if len(metadata["relations"]["version"]) != 1:
            raise Exception("Unexpected multiple versions")
        latest_version_doi = metadata["relations"]["version"][0]["last_child"]["pid_value"]

        zenodo_dois.append({
            "identifier": {
                "identifier": "https://doi.org/{}".format(dataset["conceptdoi"]),
                "identifierSource": "DOI"
            },
            "concept_doi": dataset["conceptrecid"],
            "latest_version": latest_version_doi,
            "title": title,
            "original_title": metadata["title"],
            "files": files,
            "doi_badge": dataset["conceptdoi"],
            "creators": metadata["creators"],
            "description": metadata["description"],
            "types": [],
            "version": metadata["version"] if "version" in metadata.keys() else None,
            "licenses": [metadata["license"] if "license" in metadata.keys() else {}],
            "keywords": metadata["keywords"]if "keywords" in metadata.keys() else [],
            "distributions": {
                "format": files[0]["type"] if len(files) > 0 and "type" in files[0].keys() else None,
                "size": files[0]["size"] if len(files) > 0 and "size" in files[0].keys() else None,
                "unit": {"value": "B"},
                "access": dataset["links"]["html"]
            },
            "extraProperties": [
                {
                    "category": "subjects",
                    "values": [{"value": None}]
                }
            ]
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
    d.no_annex("DATS.json")
    d.no_annex("README.md")
    d.no_annex(".conp-zenodo-crawler.json")

    r = d.create_sibling_github(repo_title,
                                github_login=token,
                                github_passwd=token)

    for bucket in dataset["files"]:
        download_file(bucket, d, dataset_dir)

    # Create DATS.json if it doesn't exist
    if not os.path.isfile(os.path.join(dataset_dir, "DATS.json")):
        create_new_dats(dataset_dir, os.path.join(dataset_dir, "DATS.json"), dataset)
        commit_push_file(dataset_dir, "DATS.json", "[conp-bot] Create DATS.json", token)

    # Add .conp-zenodo-crawler.json tracker file
    create_zenodo_tracker(os.path.join(dataset_dir, ".conp-zenodo-crawler.json"), dataset)
    commit_push_file(dataset_dir, ".conp-zenodo-crawler.json", "[conp-bot] Create .conp-zenodo-crawler.json", token)

    d.publish(to="github")

    # Create and push README.md if doesn't exist to github repo
    if create_readme(dataset, dataset_dir):
        commit_push_file(dataset_dir, "README.md", "[conp-bot] Create README.md", token)

    # Add description to Github repo
    add_description(token, repo_title, username, dataset)

    update_gitmodules(dataset_dir, r[0][1].replace(token + "@", ""))

    return d.path


def update_gitmodules(directory, github_url):
    with open(".gitmodules", "a") as f:
        f.write("""[submodule "{0}"]
  path = {0}
  url = {1}
""".format(directory, github_url))


def create_new_dats(dataset_dir, dats_path, dataset):
    with open(dats_path, "w") as f:
        data = {
            "title": dataset["original_title"],
            "identifier": dataset["identifier"],
            "creators": dataset["creators"],
            "description": dataset["description"],
            "types": dataset["types"],
            "version": dataset["version"],
            "licenses": dataset["licenses"],
            "keywords": dataset["keywords"],
            "distributions": dataset["distributions"],
            "extraProperties": dataset["extraProperties"]
        }
        # Count number of files in dataset
        num = 0
        for file in os.listdir(dataset_dir):
            if os.path.isdir(file):
                num += sum([len(list(filter(lambda x: x[0] != ".", files))) for r, d, files in os.walk(file)])
        data["extraProperties"].append({
            "category": "files",
            "values": {
                "value": str(num)
            }
        })
        json.dump(data, f, indent=4)


def update_dataset(zenodo_dataset, conp_dataset, token):
    # To update a dataset, we don't know which files have been updated
    # so we have to remove all existing files and redownload all files
    # fresh from the latest version of that zenodo dataset

    dataset_dir = conp_dataset["directory"]
    dats_dir = os.path.join(dataset_dir, "DATS.json")
    zenodo_tracker_path = os.path.join(dataset_dir, ".conp-zenodo-crawler.json")

    # Remove all data and DATS.json files
    for file_name in os.listdir(dataset_dir):
        if file_name[0] == "." or file_name == "README.md":
            continue
        api.remove(os.path.join(dataset_dir, file_name), check=False)

    d = api.Dataset(dataset_dir)

    for bucket in zenodo_dataset["files"]:
        download_file(bucket, d, dataset_dir)

    # If DATS.json isn't in downloaded files, create new DATS.json
    if not os.path.isfile(dats_dir):
        create_new_dats(dataset_dir, dats_dir, zenodo_dataset)
        commit_push_file(dataset_dir, "DATS.json", "[conp-bot] Create DATS.json", token)

    # Add/update .conp-zenodo-crawler.json tracker file
    create_zenodo_tracker(zenodo_tracker_path, zenodo_dataset)
    commit_push_file(dataset_dir, ".conp-zenodo-crawler.json", "[conp-bot] Create .conp-zenodo-crawler.json", token)

    d.publish(to="github")


def push_and_pull_request(msg, dataset_dir, token, title, repo):
    repo.git.add(dataset_dir)
    repo.git.add(".gitmodules")
    repo.git.commit("-m", "[conp-bot] " + msg)
    origin = repo.remote("origin")
    origin_url = next(origin.urls)
    if "@" not in origin_url:
        origin.set_url(origin_url.replace("https://", "https://" + token + "@"))
    repo.git.push("--set-upstream", "origin", "conp-bot/" + title)
    username = search('github.com[/,:](.*)/conp-dataset.git', origin_url).group(1)

    # Create PR
    print("Creating PR for " + title)
    r = requests.post("https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls?access_token=" + token, json={
        "title": "Zenodo crawler result ({})".format(title),
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
""".format(msg + "\n"),
        "head": username + ":conp-bot/" + title,
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


def check_requirements(repo):
    # GitHub user must have a fork of https://github.com/CONP-PCNO/conp-dataset
    # Script must be run in the base directory of a local clone of this fork
    # Git remote 'origin' of local Git clone must point to that fork
    # Local Git clone must be set to branch 'master'
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


def store(known_zenodo_tokens):
    token_path = os.path.join(os.path.expanduser('~'), ".tokens")
    with open(token_path, "r+") as f:
        data = json.load(f)
        f.seek(0)
        data["zenodo_tokens"] = known_zenodo_tokens
        json.dump(data, f, indent=4)
        f.truncate()


def switch_branch(repo, name, new=False):
    if new and name not in repo.remotes.origin.refs:
        repo.git.checkout("-b", name)
    else:
        repo.git.checkout(name)


def add_description(token, repo_title, username, dataset):
    url = "https://api.github.com/repos/{}/{}".format(username, repo_title)
    head = {"Authorization": "token {}".format(token)}
    payload = {"description": "Please don't submit any PR to this repository. "
                              "If you want to request modifications, "
                              "please contact {}".format(dataset["creators"][0]["name"])}
    r = requests.patch(url, data=json.dumps(payload), headers=head)
    if not r.ok:
        print("Problem adding description to repository {}:".format(repo_title))
        print(r.content)


def create_zenodo_tracker(path, dataset):
    with open(path, "w") as f:
        data = {
            "zenodo": {
                "concept_doi": dataset["concept_doi"],
                "version": dataset["latest_version"]
            },
            "title": dataset["original_title"]
        }
        json.dump(data, f, indent=4)


def download_file(bucket, d, dataset_dir):
    link = bucket["links"]["self"]
    if "access_token" not in link:
        d.download_url(link, archive=True if bucket["type"] == "zip" else False)
    else:  # Gotta remove URL from annex if it contains a private access token
        file_path = d.download_url(link)[0]["path"]
        annex = Repo(dataset_dir).git.annex
        annex("rmurl", file_path, link)
        annex("addurl", link.split("?")[0], "--file", file_path, "--relaxed")
        if bucket["type"] == "zip":
            api.add_archive_content(file_path, annex=AnnexRepo(dataset_dir), delete=True)


if __name__ == "__main__":
    try:
        crawl()
    except Exception:
        traceback.print_exc()
    finally:
        # Always switch branch back to master and clear .crawling touchfile
        repository = Repo()
        if repository.active_branch.name != "master":
            switch_branch(repository, "master")
        if ".crawling" in os.listdir("."):
            os.remove(".crawling")
