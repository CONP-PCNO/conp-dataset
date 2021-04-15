import csv
import datetime
import json
import os


def read_conp_dataset_dir(conp_dataset_dir_path):
    """
    Reads the conp-dataset projects directory and return the contents
    of every dataset DATS.json file in a list (one list item = one
    dataset DATS.json content).

    :param conp_dataset_dir_path: path to the conp-dataset directory
     :type conp_dataset_dir_path: str

    :return: list of dictionaries with datasets' DATS.json content
             (one list item = one dataset DATS.json content)
     :rtype: list
    """

    dataset_dirs_list = os.listdir(conp_dataset_dir_path + "/projects")

    dataset_descriptor_list = []

    for dataset in dataset_dirs_list:
        if dataset == ".touchfile":
            continue

        dats_path = conp_dataset_dir_path + "/projects/" + dataset + "/DATS.json"
        if not (os.path.exists(dats_path)):
            subdataset_content_list = read_dats_file_from_subdataset_folders(
                conp_dataset_dir_path,
                dataset,
            )
            dataset_descriptor_list.extend(subdataset_content_list)
            continue

        print("Reading file: " + dats_path)
        with open(dats_path) as dats_file:
            dats_dict = json.loads(dats_file.read())
            dataset_descriptor_list.append(dats_dict)

    return dataset_descriptor_list


def read_dats_file_from_subdataset_folders(conp_dataset_dir_path, dataset_name):
    """
    Reads DATS.json files present in the subdataset folder of a dataset_name.

    :param conp_dataset_dir_path: path to the conp-dataset_name directory
     :type conp_dataset_dir_path: str
    :param dataset_name         : name of the dataset to look for subdataset's DATS.json files
     :type dataset_name         : str

    :return: list of dictionaries with subdatasets' DATS.json content
             (one list item = one subdataset DATS.json content)
     :rtype: list
    """

    subdataset_dirs_list = os.listdir(
        conp_dataset_dir_path + "/projects/" + dataset_name,
    )

    subdataset_content = []

    for subdataset in subdataset_dirs_list:
        dats_path = os.path.join(
            conp_dataset_dir_path,
            "projects",
            dataset_name,
            subdataset,
            "DATS.json",
        )
        print("Reading file: " + dats_path)
        with open(dats_path) as dats_file:
            dats_dict = json.loads(dats_file.read())
            subdataset_content.append(dats_dict)

    return subdataset_content


def read_boutiques_cached_dir(tools_json_dir_path):
    """
    Reads the Boutiques' cache directory and return the contents
    of every JSON descriptor file in a list (one list item = one
    Boutiques' JSON descriptor content).

    :param tools_json_dir_path: path to the cached Boutiques directory
     :type tools_json_dir_path: str

    :return: list of dictionaries with Boutiques' JSON descriptor content
             (one list item = one Boutiques' JSON descriptor content)
     :rtype: list
    """

    boutiques_descriptor_list = []

    for json_file in os.listdir(tools_json_dir_path):
        print(json_file)
        if "zenodo" not in json_file or "swp" in json_file:
            continue
        json_path = tools_json_dir_path + "/" + json_file
        with open(json_path) as json_file:
            json_dict = json.loads(json_file.read())
            boutiques_descriptor_list.append(json_dict)

    return boutiques_descriptor_list


def write_csv_file(csv_file_basename, csv_content):
    """
    Write the content of a list of list into a CSV file. Example of csv_content:
        [
            ['Header_1', 'Header_2', 'Header_3' ...],
            ['Value_1',  'Value_2',  'Value_3'  ...],
            ....
        ]

    :param csv_file_basename: base name that should be given to the CSV
     :type csv_file_basename: str
    :param csv_content      : list of list with the content of the future CSV file
     :type csv_content      : list
    """

    csv_file = (
        os.getcwd()
        + "/"
        + csv_file_basename
        + "_"
        + str(datetime.date.today())
        + ".csv"
    )

    with open(csv_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(csv_content)
