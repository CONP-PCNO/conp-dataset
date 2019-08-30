import requests
import os
import json


def crawl():
    dats = get_dats()
    print(dats)


def get_dats():
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
            with open(os.path.join("projects", dataset, dats_name), "r") as f:
                dats_list.append(json.load(f))

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
            with open(os.path.join("investigators", dataset, dats_name), "r") as f:
                dats_list.append(json.load(f))

    return dats_list


def get_zenodo_datasets():
    r = requests.get("https://zenodo.org/api/records/?"
                     "type=dataset&"
                     "q=keywords:\"canadian-open-neuroscience-platform\"&"
                     "size=9999")
    return r.json()["hits"]["hits"]


if __name__ == "__main__":
    print(len(get_zenodo_datasets()))
