import requests
import os
import json
import sys
import datalad.api as api
from re import sub, search
from git import Repo


def crawl():

    # Patch arguments to get token
    token = patch_input()

    zenodo_dois = get_zenodo_dois()
    conp_dois = get_conp_dois()

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


def patch_input():
    if len(sys.argv) != 2:
        raise Exception("Need to pass only your Github access token")

    return sys.argv[1]


def get_conp_dois():
    dats_list = []

    for dataset in os.listdir("projects"):
        if dataset[0] == ".":
            continue
        dir_list = os.listdir(os.path.join("projects", dataset))
        dats_name = ""
        if "dats.json" in dir_list:
            dats_name = "dats.json"
        elif "DATS.json" in dir_list:
            dats_name = "DATS.json"
        if dats_name is not "":
            directory = os.path.join("projects", dataset)
            with open(os.path.join(directory, dats_name), "r") as f:
                dat = json.load(f)
                if "zenodo" in dat.keys():
                    new_dict = dat["zenodo"]
                    new_dict.update({"directory": directory})
                    dats_list.append(new_dict)

    for dataset in os.listdir("investigators"):
        if dataset[0] == ".":
            continue
        dir_list = os.listdir(os.path.join("investigators", dataset))
        dats_name = ""
        if "dats.json" in dir_list:
            dats_name = "dats.json"
        elif "DATS.json" in dir_list:
            dats_name = "DATS.json"
        if dats_name is not "":
            directory = os.path.join("investigators", dataset)
            with open(os.path.join(directory, dats_name), "r") as f:
                dat = json.load(f)
                if "zenodo" in dat.keys():
                    new_dict = dat["zenodo"]
                    new_dict.update({"directory": directory})
                    dats_list.append(new_dict)

    return dats_list


def get_zenodo_dois():
    zenodo_dois = []
    # https://zenodo.org/api/records/?q=3363060&size=1
    r = requests.get("https://zenodo.org/api/records/?"
                     # "type=dataset&"
                     # "q=keywords:\"canadian-open-neuroscience-platform\"&"
                     # "q=keywords:\"analysis\"&"
                     "q=3363060&"
                     "size=1").json()["hits"]["hits"]
    for dataset in r:
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
            "files": files
        })

    return zenodo_dois


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

    # Update dats.json or DATS.json or create one if it doesn't exist
    if update_dats(os.path.join(dataset_dir, "dats.json"), dataset):
        api.add(os.path.join(dataset_dir, "dats.json"))
    elif update_dats(os.path.join(dataset_dir, "DATS.json"), dataset):
        api.add(os.path.join(dataset_dir, "DATS.json"))
    else:
        create_new_dats(os.path.join(dataset_dir, "dats.json"), dataset)
        api.add(os.path.join(dataset_dir, "dats.json"))

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
    elif update_dats(os.path.join(dataset_dir, "DATS.json"), zenodo_dataset):
        api.add(os.path.join(dataset_dir, "DATS.json"))
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
    username = search('github.com/(.*)/conp-dataset.git', origin_url).group(1)
    r = requests.post("https://api.github.com/repos/CONP-PCNO/conp-dataset/pulls?access_token=" + token, data={
        "title": "Zenodo crawler results",
        "body": "Changes: \n" + "\n".join(msg),
        "head": username + ":master",
        "base": "master",
        "draft": True
    })
    if r.status_code != 201:
        raise Exception("Error while creating pull request")


if __name__ == "__main__":
    crawl()
