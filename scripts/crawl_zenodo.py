import requests
import os
import json


def crawl():
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
                # Update
        else:
            # Update


    print(conp_dois)


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
                     "q=keywords:\"analysis\"&"
                     "size=20").json()["hits"]["hits"]
    for dataset in r:
        concept_doi = dataset["conceptrecid"]
        if len(dataset["metadata"]["relations"]["version"]) != 1:
            raise Exception("Unexpected multiple versions")
        latest_version_doi = dataset["metadata"]["relations"]["version"][0]["last_child"]["pid_value"]
        zenodo_dois.append({
            "concept_doi": concept_doi,
            "latest_version": latest_version_doi
        })

    return zenodo_dois


def verify_duplicates(zenodo_dois, conp_dois):
    concept_dois = list(map(lambda x: x["concept_doi"], zenodo_dois))
    if len(concept_dois) != len(set(concept_dois)):
        raise Exception("Concept DOI duplicates exists in zenodo list")
    version_dois = list(map(lambda x: x["latest_version"], zenodo_dois))
    if len(version_dois) != len(set(version_dois)):
        raise Exception("Version DOI duplicates exists in zenodo list")
    concept_dois = list(map(lambda x: x["concept_doi"], conp_dois))
    if len(concept_dois) != len(set(concept_dois)):
        raise Exception("Concept DOI duplicates exists in conp list")
    version_dois = list(map(lambda x: x["version"], conp_dois))
    if len(version_dois) != len(set(version_dois)):
        raise Exception("Version DOI duplicates exists in conp list")
    directories = list(map(lambda x: x["directory"], conp_dois))
    if len(directories) != len(set(directories)):
        raise Exception("Directory duplicates exists in conp list")


if __name__ == "__main__":
    crawl()