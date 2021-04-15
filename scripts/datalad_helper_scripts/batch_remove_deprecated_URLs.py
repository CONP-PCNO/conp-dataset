import getopt
import json
import os
import re
import sys
import traceback

import git


def parse_input(argv):
    """
    Displays the script's help section and parses the options given to the script.

    :param argv: command line arguments
     :type argv: array

    :return: parsed and validated script options
     :rtype: dict
    """

    script_options = {}

    description = (
        "\nThis script can be used to remove from git-annex a series of URLs matching"
        " a specific pattern.\n"
        "\t- To run the script and print out the URLs that will be removed, use options"
        " -d <dataset path> -u <invalid URL regex>.\n"
        "\t- After examination of the result of the script, rerun the script with the same"
        " option and add the -c argument for actual removal of the URLs.\n"
        "\t- Option -v prints out progress of the script in the terminal.\n"
    )

    usage = (
        f"\nusage  : python {__file__} -d <DataLad dataset directory path> -u <invalid URL regex>\n"
        "\noptions: \n"
        "\t-d: path to the DataLad dataset to work on\n"  # noqa: E131
        "\t-u: regular expression for invalid URLs to remove from git-annex\n"  # noqa: E131
        "\t-c: confirm that the removal of the URLs should be performed. By default it will just print out what needs to be removed for validation\n"  # noqa: E501,E131
        "\t-v: verbose\n"  # noqa: E131
    )

    try:
        opts, args = getopt.getopt(argv, "hcd:u:")
    except getopt.GetoptError:
        sys.exit()

    script_options["run_removal"] = False
    script_options["verbose"] = False

    if not opts:
        print(description + usage)
        sys.exit()

    for opt, arg in opts:
        if opt == "-h":
            print(description + usage)
            sys.exit()
        elif opt == "-d":
            script_options["dataset_path"] = arg
        elif opt == "-u":
            script_options["invalid_url_regex"] = arg
        elif opt == "-c":
            script_options["run_removal"] = True
        elif opt == "-v":
            script_options["verbose"] = True

    if "dataset_path" not in script_options.keys():
        print(
            "\n\t* ----------------------------------------------------------------------------------------------------------------------- *"  # noqa: E501
            "\n\t* ERROR: a path to the DataLad dataset to process needs to be given as an argument to the script by using the option `-d` *"  # noqa: E501
            "\n\t* ----------------------------------------------------------------------------------------------------------------------- *",  # noqa: E501
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(script_options["dataset_path"]):
        print(
            f"\n\t* ------------------------------------------------------------------------------ *"
            f"\n\t* ERROR: {script_options['dataset_path']} does not appear to be a valid path   "
            f"\n\t* ------------------------------------------------------------------------------ *",
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(os.path.join(script_options["dataset_path"], ".datalad")):
        print(
            f"\n\t* ----------------------------------------------------------------------------------- *"
            f"\n\t* ERROR: {script_options['dataset_path']} does not appear to be a DataLad dataset   "
            f"\n\t* ----------------------------------------------------------------------------------- *",
        )
        print(description + usage)
        sys.exit()

    if "invalid_url_regex" not in script_options.keys():
        print(
            "\n\t* --------------------------------------------------------------------------------------------------- *"  # noqa: E501
            "\n\t* ERROR: a regex for invalid URLs to remove should be provided to the script by using the option `-u` *"  # noqa: E501
            "\n\t* --------------------------------------------------------------------------------------------------- *",  # noqa: E501
        )
        print(description + usage)
        sys.exit()

    return script_options


def get_files_and_urls(dataset_path, annex):
    """
    Runs git annex whereis in the dataset directory to retrieve
    a list of annexed files with their URLs' location.

    :param dataset_path: full path to the DataLad dataset
     :type dataset_path: string
    :param annex: the git annex object
     :type annex: object

    :return: files path and there URLs organized as follows:
             {
                <file-1_path> => [file-1_url-1, file-1_url-2 ...]
                <file-2_path> => [file-2_url-1, file-2_url-2 ...]
                ...
             }
     :rtype: dict
    """

    current_path = os.path.dirname(os.path.realpath(__file__))

    results = {}
    try:
        os.chdir(dataset_path)
        annex_results = annex("whereis", ".", "--json")
        results_list = annex_results.split("\n")
        for annex_result_item in results_list:
            r_json = json.loads(annex_result_item)
            file_path = r_json["file"]
            file_urls = []
            for entry in r_json["whereis"]:
                file_urls.extend(entry["urls"])
            results[file_path] = file_urls
    except Exception:
        traceback.print_exc()
        sys.exit()
    finally:
        os.chdir(current_path)

    return results


def filter_invalid_urls(files_and_urls_dict, regex_pattern):
    """
    Filters out the URLs that need to be removed based on a regular
    expression pattern.

    :param files_and_urls_dict: files' path and their respective URLs.
     :type files_and_urls_dict: dict
    :param regex_pattern: regular expression pattern for URL filtering
     :type regex_pattern: str

    :return: filtered URLs per file
     :rtype: dict
    """

    filtered_dict = {}
    for file_path in files_and_urls_dict.keys():
        filtered_urls_list = filter(
            lambda x: re.search(regex_pattern, x),
            files_and_urls_dict[file_path],
        )
        filtered_dict[file_path] = filtered_urls_list

    return filtered_dict


def remove_invalid_urls(filtered_file_urls_dict, script_options, annex):
    """
    Removes URLs listed in the filtered dictionary from the files.

    :param filtered_file_urls_dict: filtered URLs to remove per file
     :type filtered_file_urls_dict: dict
    :param script_options: options give to the script
     :type script_options: dict
    :param annex: the git annex object
     :type annex: object
    """

    dataset_path = script_options["dataset_path"]
    current_path = os.path.dirname(os.path.realpath(__file__))

    try:
        os.chdir(dataset_path)
        for file_path in filtered_file_urls_dict.keys():
            for url in filtered_file_urls_dict[file_path]:
                if script_options["run_removal"]:
                    if script_options["verbose"]:
                        print(f"\n => Running `git annex rmurl {file_path} {url}`\n")
                    annex("rmurl", file_path, url)
                else:
                    print(
                        f"\nWill be running `git annex rmurl {file_path} {url}`\n",
                    )
    except Exception:
        traceback.print_exc()
    finally:
        os.chdir(current_path)


if __name__ == "__main__":

    script_options = parse_input(sys.argv[1:])

    repo = git.Repo(script_options["dataset_path"])
    annex = repo.git.annex

    # fetch files and urls attached to the file
    if script_options["verbose"]:
        print(
            f"\n => Reading {script_options['dataset_path']} and grep annexed files with their URLs\n",
        )
    files_and_urls_dict = get_files_and_urls(script_options["dataset_path"], annex)

    # grep only the invalid URLs that need to be removed from the annexed files
    regex_pattern = re.compile(script_options["invalid_url_regex"])
    if script_options["verbose"]:
        print(
            f"\n => Grep the invalid URLs based on the regular expression {regex_pattern}",
        )
    filtered_file_urls_dict = filter_invalid_urls(files_and_urls_dict, regex_pattern)

    # remove the invalid URLs found for each annexed file
    remove_invalid_urls(filtered_file_urls_dict, script_options, annex)
