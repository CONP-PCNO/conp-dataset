import csv
import datetime
import getopt
import json
import os
import sys


def main(argv):

    conp_dataset_dir = parse_input(argv)

    csv_content = read_conp_dataset_dir(conp_dataset_dir)

    write_csv_file(csv_content)


def parse_input(argv):

    conp_dataset_dir = None

    description = (
        "\nThis tool facilitates the aggregation of data provenance for reporting purposes."
        " It will read DATS files and print out a summary of data provenance based on the `origin`"
        " fields present in the DATS.json files of every dataset present in conp-dataset directory.\n"
    )
    usage = (
        "\n"
        "usage  : python " + __file__ + " -d <conp-dataset directory path>\n\n"
        "options: \n"
        "\t-d: path to the conp-dataset directory to parse\n"
    )

    try:
        opts, args = getopt.getopt(argv, "hd:")
    except getopt.GetoptError:
        sys.exit()

    for opt, arg in opts:
        if opt == "-h":
            print(description + usage)
            sys.exit()
        elif opt == "-d":
            conp_dataset_dir = arg

    if not conp_dataset_dir:
        print(
            "a path to the conp-dataset needs to be given as an argument to the script by using the option `-d`",
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(conp_dataset_dir + "/projects"):
        print(
            conp_dataset_dir
            + "does not appear to be a valid path and does not include a `projects` directory",
        )
        print(description + usage)
        sys.exit()

    return conp_dataset_dir


def read_conp_dataset_dir(conp_dataset_dir):

    dataset_dirs_list = os.listdir(conp_dataset_dir + "/projects")

    csv_content = [
        [
            "Dataset",
            "Principal Investigator",
            "Consortium",
            "Institution",
            "City",
            "Province",
            "Country",
        ],
    ]

    for dataset in dataset_dirs_list:
        if dataset in [".touchfile", ".DS_Store"]:
            continue
        dats_path = conp_dataset_dir + "/projects/" + dataset + "/DATS.json"
        if not (os.path.exists(dats_path)):
            subdataset_content_list = look_for_dats_file_in_subfolders(
                conp_dataset_dir,
                dataset,
            )
            csv_content.extend(subdataset_content_list)
            continue

        parsed_result = parse_dats_json_file(dats_path)
        csv_content.append(parsed_result)

    return csv_content


def look_for_dats_file_in_subfolders(conp_dataset_dir, dataset):

    subdataset_dirs_list = os.listdir(conp_dataset_dir + "/projects/" + dataset)

    subdataset_content = []

    for subdataset in subdataset_dirs_list:
        dats_path = (
            conp_dataset_dir + "/projects/" + dataset + "/" + subdataset + "/DATS.json"
        )
        parsed_result = parse_dats_json_file(dats_path)
        subdataset_content.append(parsed_result)

    return subdataset_content


def parse_dats_json_file(dats_path):

    print(dats_path)

    with open(dats_path, encoding="utf8") as dats_file:
        dats_dict = json.loads(dats_file.read())

    extra_properties = dats_dict["extraProperties"]
    values_dict = {}
    for extra_property in extra_properties:
        values_dict[extra_property["category"]] = ", ".join(
            str(value) for value in [exp["value"] for exp in extra_property["values"]]
        )

    creators = dats_dict["creators"]
    for creator in creators:
        if "roles" in creator.keys():
            for role in creator["roles"]:
                if (
                    role["value"] == "Principal Investigator"
                    and "name" in creator.keys()
                ):
                    values_dict["principal_investigator"] = creator["name"]

    return [
        dats_dict["title"],
        values_dict["principal_investigator"]
        if "principal_investigator" in values_dict
        else "",
        values_dict["origin_consortium"] if "origin_consortium" in values_dict else "",
        values_dict["origin_institution"]
        if "origin_institution" in values_dict
        else "",
        values_dict["origin_city"] if "origin_city" in values_dict else "",
        values_dict["origin_province"] if "origin_province" in values_dict else "",
        values_dict["origin_country"] if "origin_country" in values_dict else "",
    ]


def write_csv_file(csv_content):

    csv_file = (
        os.getcwd() + "/dataset_provenance_" + str(datetime.date.today()) + ".csv"
    )

    with open(csv_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(csv_content)


if __name__ == "__main__":
    main(sys.argv[1:])
