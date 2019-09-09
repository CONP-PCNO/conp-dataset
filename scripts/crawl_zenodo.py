import requests
import os
import json
import sys
from zipfile import ZipFile
import datalad.api as api
from re import sub


def crawl():

    # Get github username and password
    token = get_token()

    zenodo_dois = get_zenodo_dois()
    conp_dois = get_conp_dois()

    # Verify no duplicates in both lists
    verify_duplicates(zenodo_dois, conp_dois)

    for dataset in zenodo_dois:
        index = next((i for (i, d) in enumerate(conp_dois) if d["concept_doi"] == dataset["concept_doi"]), None)

        # If the zenodo dataset exists in conp datasets
        if index is not None:
            # If the conp dataset version isn't the lastest, update
            if dataset["latest_version"] != conp_dois[index]["version"]:
                pass
        else:
            create_new_dataset(dataset, token)


def get_token():
    if len(sys.argv) != 2:
        raise Exception("Need to pass Github access token")

    token = sys.argv[1]

    return token


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
    r = requests.get("https://zenodo.org/api/records/?"
                     # "type=dataset&"
                     # "q=keywords:\"canadian-open-neuroscience-platform\"&"
                     # "q=keywords:\"analysis\"&"
                     "q=3363060"
                     "size=1").json()["hits"]["hits"]
    for dataset in r:
        concept_doi = dataset["conceptrecid"]
        if len(dataset["metadata"]["relations"]["version"]) != 1:
            raise Exception("Unexpected multiple versions")
        latest_version_doi = dataset["metadata"]["relations"]["version"][0]["last_child"]["pid_value"]
        zip_files = []
        for bucket in dataset["files"]:
            if bucket["type"] == "zip":
                zip_files.append(bucket["links"]["self"])
        if len(zip_files) < 1:
            print("Zenodo dataset " + dataset["title"] + " does not contain a zip file")
        zenodo_dois.append({
            "concept_doi": concept_doi,
            "latest_version": latest_version_doi,
            "title": clean(dataset["metadata"]["title"]),
            "files": zip_files
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
    file_link = list(map(lambda x: x["file"], zenodo_dois))
    if len(file_link) != len(set(file_link)):
        raise Exception("File link duplicates exists in zenodo list")
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
    dir = os.path.join("projects", dataset["title"])
    api.create(dir)
    api.create_sibling_github("conp-dataset-" + dataset["title"],
                              dataset=dir,
                              recursive=True,
                              github_login=token,
                              github_passwd=token)
    for file_url in dataset["files"]:
        r = requests.get(file_url)
        if r.ok:
            with open("temp.zip", "wb") as f:
                f.write(r.content)
            with ZipFile("temp.zip", "r") as f:
                f.extractall(dir)
        else:
            raise Exception("Failed to download zip file: " + file_url)


if __name__ == "__main__":
    crawl()
