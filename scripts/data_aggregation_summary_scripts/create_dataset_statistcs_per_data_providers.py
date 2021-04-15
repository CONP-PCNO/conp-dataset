import getopt
import os
import sys

import lib.Utility as Utility


def main(argv):

    # create the getopt table + read and validate the options given to the script
    conp_dataset_dir = parse_input(argv)

    # read the content of the DATS.json files present in the conp-dataset directory
    dataset_descriptor_list = Utility.read_conp_dataset_dir(conp_dataset_dir)

    # digest the content of the DATS.json files into a summary of variables of interest
    datasets_summary_dict = {}
    i = 0
    for dataset in dataset_descriptor_list:
        datasets_summary_dict[i] = parse_dats_information(dataset)
        i += 1

    # create the summary statistics of the variables of interest organized per data providers
    csv_content = [
        [
            "Data Provider",
            "Number Of Datasets",
            "Number Of Datasets Requiring Authentication",
            "Total Number Of Files",
            "Total Size (GB)",
            "Keywords Describing The Data",
        ],
    ]
    for data_provider in ["braincode", "frdr", "loris", "osf", "zenodo"]:
        summary_list = get_stats_for_data_provider(datasets_summary_dict, data_provider)
        csv_content.append(summary_list)

    # write the summary statistics into a CSV file
    Utility.write_csv_file("dataset_summary_statistics_per_data_providers", csv_content)


def parse_input(argv):
    """
    Creates the GetOpt table + read and validate the options given when calling the script.

    :param argv: command-line arguments
     :type argv: list

    :return: the path to the conp-dataset directory
     :rtype: str
    """

    conp_dataset_dir_path = None

    description = (
        "\nThis tool facilitates the creation of statistics per data providers for reporting purposes."
        " It will read DATS files and print out a summary per data providers based on the following list"
        "of DATS fields present in the DATS. json of every dataset present in the conp-dataset/projects"
        "directory.\n Queried fields: <distribution->access->landingPage>; "
        "<distributions->access->authorizations>; "
        "<distributions->size>; <extraProperties->files>; <keywords>\n"
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
            conp_dataset_dir_path = arg

    if not conp_dataset_dir_path:
        print(
            "a path to the conp-dataset needs to be given as an argument to the script by using the option `-d`",
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(conp_dataset_dir_path + "/projects"):
        print(
            conp_dataset_dir_path
            + "does not appear to be a valid path and does not include a `projects` directory",
        )
        print(description + usage)
        sys.exit()

    return conp_dataset_dir_path


def parse_dats_information(dats_dict):
    """
    Parse the content of the DATS dictionary and grep the variables of interest for
    the summary statistics.

    :param dats_dict: dictionary with the content of a dataset's DATS.json file
     :type dats_dict: dict

    :return: dictionary with the variables of interest to use to produce the
             summary statistics
     :rtype: dict
    """

    extra_properties = dats_dict["extraProperties"]
    keywords = dats_dict["keywords"]

    values_dict = {
        "extraProperties": {},
        "keywords": [],
    }
    for extra_property in extra_properties:
        values_dict[extra_property["category"]] = extra_property["values"][0]["value"]
    for keyword in keywords:
        values_dict["keywords"].append(keyword["value"])

    authorization = "unknown"
    if "authorizations" in dats_dict["distributions"][0]["access"]:
        authorization = dats_dict["distributions"][0]["access"]["authorizations"][0][
            "value"
        ]

    return {
        "title": dats_dict["title"],
        "data_provider": dats_dict["distributions"][0]["access"]["landingPage"],
        "authorization": authorization,
        "dataset_size": dats_dict["distributions"][0]["size"],
        "size_unit": dats_dict["distributions"][0]["unit"]["value"],
        "number_of_files": values_dict["files"] if "files" in values_dict else "",
        "keywords": values_dict["keywords"] if "keywords" in values_dict else "",
    }


def get_stats_for_data_provider(dataset_summary_dict, data_provider):
    """
    Produces a summary statistics per data provider (Zenodo, OSF, LORIS...) of the
    identified variables of interest.

    :param dataset_summary_dict: dictionary with the variables of interest for the summary
     :type dataset_summary_dict: dict
    :param data_provider       : name of the data provider
     :type data_provider       : str

    :return: list with the summary statistics on the variables for the data provider
     :rtype: list
    """

    dataset_number = 0
    requires_login = 0
    total_size = 0
    total_files = 0
    keywords_list = []

    for index in dataset_summary_dict:

        dataset_dict = dataset_summary_dict[index]
        if data_provider not in dataset_dict["data_provider"]:
            continue

        dataset_number += 1
        if isinstance(dataset_dict["number_of_files"], str):
            total_files += int(dataset_dict["number_of_files"].replace(",", ""))
        else:
            total_files += dataset_dict["number_of_files"]

        if dataset_dict["authorization"].lower() in ["private", "restricted"]:
            requires_login += 1

        if dataset_dict["size_unit"].lower() == "b":
            total_size += dataset_dict["dataset_size"] / pow(1024, 3)
        elif dataset_dict["size_unit"].lower() == "kb":
            total_size += dataset_dict["dataset_size"] / pow(1024, 2)
        elif dataset_dict["size_unit"].lower() == "mb":
            total_size += dataset_dict["dataset_size"] / 1024
        elif dataset_dict["size_unit"].lower() == "gb":
            total_size += dataset_dict["dataset_size"]
        elif dataset_dict["size_unit"].lower() == "tb":
            total_size += dataset_dict["dataset_size"] * 1024
        elif dataset_dict["size_unit"].lower() == "pb":
            total_size += dataset_dict["dataset_size"] * pow(1024, 2)

        for keyword in dataset_dict["keywords"]:
            if keyword not in keywords_list:
                if keyword == "canadian-open-neuroscience-platform":
                    continue
                keywords_list.append(keyword)

    return [
        data_provider,
        str(dataset_number),
        str(requires_login),
        str(total_files),
        str(round(total_size)),
        ", ".join(keywords_list),
    ]


if __name__ == "__main__":
    main(sys.argv[1:])
