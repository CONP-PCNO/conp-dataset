import requests
import os
import json
import argparse
import datalad.api as api
from re import sub, search
from git import Repo


def crawl():

    # Patch arguments to get token
    token, verbose = parse_args()

    zenodo_dois = get_zenodo_dois(verbose)
    conp_dois = get_conp_dois(verbose)
    if verbose:
        print("DOIs found on Zenodo: " + str(zenodo_dois))
        print("DOIs found in CONP dataset: "+ str(conp_dois))

    # Verify no duplicates in both lists
    verify_duplicates(zenodo_dois, conp_dois)

    commit_msg = []

    for dataset in zenodo_dois:
        index = next((i for (i, d) in enumerate(conp_dois) if d["concept_doi"] == dataset["concept_doi"]), None)

        # If the zenodo dataset exists in conp datasets
        if index is not None:
            # If the conp dataset version isn't the lastest, update
            if dataset["latest_version"] != conp_dois[index]["version"]:
                update_dataset(dataset, conp_dois[index])
                commit_msg.append("update " + dataset["title"])
        else:
            create_new_dataset(dataset, token)
            commit_msg.append("create " + dataset["title"])

    if len(commit_msg) >= 1:
        push_and_pull_request(commit_msg, token)
    else:
        print("No changes detected")


def parse_args():
    parser = argparse.ArgumentParser(description='''
    CONP Zenodo crawler. Performs the following steps:
    1. searches for all datasets in Zenodo with the keyword 
       'canadian-open-neuroscience-platform',
    2. downloads or updates them locally, 
    3. commits and push to a GitHub account (identified by parameter github_token),
    4. creates a pull request to https://github.com/CONP-PCNO/conp-dataset.

    Requirements:
    * run from the basedir of a local clone of conp-dataset
    * conp-dataset has to be set to branch 'master'
    ''')
    parser.add_argument("github_token", action="store", help="GitHub access token")
    parser.add_argument("--verbose", action="store_true", help="Print debug information")
    args = parser.parse_args()

    return args.github_token, args.verbose


def get_conp_dois(verbose=False):
    dats_list = []
    dataset_container_dirs = get_dataset_container_dirs()

    for dataset_container in dataset_container_dirs:
        for dataset in os.listdir(dataset_container):
            if dataset[0] == ".":
                continue
            dir_list = os.listdir(os.path.join(dataset_container, dataset))
            dats_name = ""
            if "dats.json" in dir_list:
                dats_name = "dats.json"
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


def get_zenodo_dois(verbose=False):
    zenodo_dois = []
    r = query_zenodo(verbose)
    for dataset in r:
        doi_badge = dataset["conceptdoi"]
        concept_doi = dataset["conceptrecid"]
        title = clean(dataset["metadata"]["title"])
        if len(dataset["metadata"]["relations"]["version"]) != 1:
            raise Exception("Unexpected multiple versions")
        latest_version_doi = dataset["metadata"]["relations"]["version"][0]["last_child"]["pid_value"]
        files = []
        for bucket in dataset["files"]:
            files.append(bucket)
        if len(files) < 1:
            print("Zenodo dataset " + title + " does not contain any file")
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


def create_new_dataset(dataset, token):
    dataset_dir = os.path.join("projects", dataset["title"])
    d = api.Dataset(dataset_dir)
    d.create()
    repo_title = ("conp-dataset-" + dataset["title"])[0:100]
    r = d.create_sibling_github(repo_title,
                                github_login=token,
                                github_passwd=token)
    update_gitmodules(dataset_dir, r[0][1].replace(token + "@", ""))

    for bucket in dataset["files"]:
        d.download_url(bucket["links"]["self"], archive=True if bucket["type"] == "zip" else False)

    # Update dats.json or create one if it doesn't exist
    if update_dats(os.path.join(dataset_dir, "dats.json"), dataset):
        api.add(os.path.join(dataset_dir, "dats.json"))
    else:
        create_new_dats(os.path.join(dataset_dir, "dats.json"), dataset)
        api.add(os.path.join(dataset_dir, "dats.json"))

    # Create README.md if doesn't exist
    if create_readme(dataset, dataset_dir):
        api.add(os.path.join(dataset_dir, "README.md"))

    d.publish(to="github")


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


def update_dataset(zenodo_dataset, conp_dataset):
    # To update a dataset, we don't know which files have been updated
    # so we have to remove all existing files and redownload all files
    # fresh from the latest version of that zenodo dataset

    dataset_dir = conp_dataset["directory"]
    for file_name in os.listdir(dataset_dir):
        if file_name[0] == "." or file_name.lower() == "dats.json":
            continue
        api.remove(os.path.join(dataset_dir, file_name), check=False)

    d = api.Dataset(dataset_dir)

    for bucket in zenodo_dataset["files"]:
        d.download_url(bucket["links"]["self"], archive=True if bucket["type"] == "zip" else False)

    # Update dats.json or DATS.json or create one if it doesn't exist
    if update_dats(os.path.join(dataset_dir, "dats.json"), zenodo_dataset):
        api.add(os.path.join(dataset_dir, "dats.json"))
    else:
        raise Exception("No dats.json file in existing dataset, aborting")

    d.publish(to="github")


def push_and_pull_request(msg, token):
    repo = Repo()
    repo.git.add(".")
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
- [x] A `dats.json` file, at the root of the dataset
- [ ] If configuration is required (for instance to enable a special remote), a `config.sh` script at the root of the dataset
- [x] A DOI (see instructions in [contribution guide](https://github.com/CONP-PCNO/conp-dataset/blob/master/.github/CONTRIBUTING.md), and corresponding badge in `README.md`

Functional checks:
- [x] Dataset can be installed using DataLad, recursively if it has sub-datasets
- [x] Every data file has a URL
- [x] Every data file can be retrieved or requires authentication
- [ ] `dats.json` is a valid DATs model
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

Crawled from Zenodo: [![DOI](https://www.zenodo.org/badge/DOI/{1}.svg)](https://doi.org/{1})"""
                    .format(dataset["title"], dataset["doi_badge"]))
        return True
    return False


if __name__ == "__main__":
    crawl()
