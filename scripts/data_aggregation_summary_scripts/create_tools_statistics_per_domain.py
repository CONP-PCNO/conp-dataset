"""Docstring."""
import getopt
import os
import sys

import lib.Utility as Utility


def main(argv):
    """Doctring."""
    # create the getopt table + read and validate the options given to the script
    tools_json_dir_path = parse_input(argv)

    # read the content of the DATS.json files present in the boutiques's cached
    # directory present in ~
    tool_descriptor_list = Utility.read_boutiques_cached_dir(tools_json_dir_path)

    # digest the content of the DATS.json files into a summary of variables of interest
    tools_summary_dict = {}
    i = 0
    for tool in tool_descriptor_list:
        tools_summary_dict[i] = parse_json_information(tool)
        i += 1

    # create the summary statistics of the variables of interest organized per
    # domain of application
    csv_content = [
        [
            "Domain of Application",
            "Number Of Tools",
            "Containers",
            "Execution Capacity",
        ],
    ]
    for field in [
        "Neuroinformatics",
        "Bioinformatics",
        "MRI",
        "EEG",
        "Connectome",
        "BIDS-App",
    ]:
        summary_list = get_stats_per_domain(tools_summary_dict, field)
        csv_content.append(summary_list)

    # write the summary statistics into a CSV file
    Utility.write_csv_file("tools_summary_statistics_per_domain", csv_content)


def parse_input(argv):
    """
    Create the GetOpt table + read and validate the options given when calling the script.

    :param argv: command-line arguments
     :type argv: list

    :return: the path to the tools directory containing the Boutiques JSON descriptors
             (typically ~/.cache/boutiques/production)
     :rtype: str
    """
    tools_dir_path = None

    description = (
        "\nThis tool facilitates the creation of tools summary statistics per domain of application for "
        "reporting purposes. It will read Boutiques's JSON files and print out a summary per domain based "
        "on the following list of tags: \nNeuroinformatics, Bioinformatics, MRI, EEG, Connectome, BIDS-App.\n"
    )
    usage = (
        "\n"
        "usage  : python "
        + __file__
        + " -d <path to the Boutiques's JSON cached directory to parse."
        " (typically ~/.cache/boutiques/production>\n\n"
        "options: \n"
        "\t-d: path to the Boutiques's JSON cached directory to parse."
        " (typically ~/.cache/boutiques/production>\n\n"
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
            tools_dir_path = arg

    if not tools_dir_path:
        print(
            "a path to the Boutiques's JSON cached directory needs to be "
            "given as an argument to the script by using the option `-d`",
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(tools_dir_path):
        print(tools_dir_path + "does not appear to be a valid path")
        print(description + usage)
        sys.exit()

    return tools_dir_path


def parse_json_information(json_dict):
    """
    Parse the content of the JSON dictionary and grep the variables of interest for the summary statistics.

    :param json_dict: dictionary with the content of a tool JSON descriptor file
     :type json_dict: dict

    :return: dictionary with the variables of interest to use to produce the
             summary statistics
     :rtype: dict
    """
    tool_summary_dict = {
        "title": json_dict["name"],
        "container_type": None,
        "domain": None,
        "online_platform_urls": None,
    }

    if "container-image" in json_dict and "type" in json_dict["container-image"]:
        tool_summary_dict["container_type"] = json_dict["container-image"]["type"]

    if "tags" in json_dict and "domain" in json_dict["tags"]:
        tool_summary_dict["domain"] = [x.lower() for x in json_dict["tags"]["domain"]]

    if "online-platform-urls" in json_dict:
        tool_summary_dict["online_platform_urls"] = json_dict["online-platform-urls"]

    return tool_summary_dict


def get_stats_per_domain(tool_summary_dict, domain):
    """
    Produce a summary statistics per domain (Neuroinformatics, Bioinformatics, MRI, EEG...) of the identified variables of interest.  # noqa: E501.

    :param tool_summary_dict: dictionary with the variables of interest for the summary
     :type tool_summary_dict: dict
    :param domain           : name of the domain of application
     :type domain           : str

    :return: list with the summary statistics on the variables for the domain of application
     :rtype: list
    """
    container = {
        "docker": 0,
        "singularity": 0,
    }
    number_of_tools = 0
    number_of_cbrain_tools = 0

    for index in tool_summary_dict:

        tool_dict = tool_summary_dict[index]

        if not tool_dict["domain"]:
            continue

        if domain.lower() not in tool_dict["domain"] and domain != "BIDS-App":
            continue

        if domain == "BIDS-App" and "bids app" not in tool_dict["title"].lower():
            continue

        number_of_tools += 1

        if tool_dict["container_type"] == "docker":
            container["docker"] += 1
        elif tool_dict["container_type"] == "singularity":
            container["singularity"] += 1

        print(tool_dict["online_platform_urls"])

        if (
            tool_dict["online_platform_urls"]
            and "https://portal.cbrain.mcgill.ca" in tool_dict["online_platform_urls"]
        ):
            number_of_cbrain_tools += 1

    return [
        domain,
        str(number_of_tools),
        f'Docker ({str(container["docker"])}); Singularity ({str(container["singularity"])})',
        "CBRAIN (" + str(number_of_cbrain_tools) + ")",
    ]


if __name__ == "__main__":
    main(sys.argv[1:])
