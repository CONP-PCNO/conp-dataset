import json
import getopt
import sys
import os
import git
import subprocess
import traceback
import re




def main(argv):

    script_options = parse_input(argv)

    repo = git.Repo(script_options['dataset_path'])
    annex = repo.git.annex
    files_and_urls_dict = get_files_and_urls(script_options, annex)

    regex_pattern = re.compile(script_options['invalid_url_regex'])
    filtered_file_urls_dict = filter_invalid_urls(files_and_urls_dict, regex_pattern)

    remove_url(filtered_file_urls_dict, script_options, annex)

def parse_input(argv):

    script_options = {}

    description = f"\n********************* DESCRIPTION TO BE WRITTEN ************************\n"

    usage = (
        f"\nusage  : python {__file__} -d <DataLad dataset directory path> -u <invalid URL regex>\n"
        f"\noptions: \n"
            f"\t-d: path to the DataLad dataset to work on\n"
            f"\t-u: regular expression for invalid URLs to remove from git-annex\n"
            f"\t-c: confirm that the removal of the URLs should be performed. "
                    f"By default it will just print out what needs to be removed for validation\n"
    )

    try:
        opts, args = getopt.getopt(argv, "hcd:u:")
    except getopt.GetoptError:
        sys.exit()

    script_options['run_removal'] = False
    script_options['verbose']     = False

    if not opts:
        print(description + usage)
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print(description + usage)
            sys.exit()
        elif opt == '-d':
            script_options['dataset_path'] = arg
        elif opt == '-u':
            script_options['invalid_url_regex'] = arg
        elif opt == '-c':
            script_options['run_removal'] = True
        elif opt == '-v':
            script_options['verbose'] = True

    if 'dataset_path' not in script_options.keys():
        print(
            '\n\t* ----------------------------------------------------------------------------------------------------------------------- *'
            '\n\t* ERROR: a path to the DataLad dataset to process needs to be given as an argument to the script by using the option `-d` *'
            '\n\t* ----------------------------------------------------------------------------------------------------------------------- *'
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(script_options['dataset_path']):
        print(
            f"\n\t* ------------------------------------------------------------------------------ *"
            f"\n\t* ERROR: {script_options['dataset_path']} does not appear to be a valid path   "
            f"\n\t* ------------------------------------------------------------------------------ *"
        )
        print(description + usage)
        sys.exit()

    if not os.path.exists(os.path.join(script_options['dataset_path'], '.datalad')):
        print(
            f"\n\t* ----------------------------------------------------------------------------------- *"
            f"\n\t* ERROR: {script_options['dataset_path']} does not appear to be a DataLad dataset   "
            f"\n\t* ----------------------------------------------------------------------------------- *"
        )
        print(description + usage)
        sys.exit()

    if 'invalid_url_regex' not in script_options.keys():
        print(
            '\n\t* --------------------------------------------------------------------------------------------------- *'
            '\n\t* ERROR: a regex for invalid URLs to remove should be provided to the script by using the option `-u` *'            
            '\n\t* --------------------------------------------------------------------------------------------------- *'
        )
        print(description + usage)
        sys.exit()

    return script_options


def read_dataset_directory(script_options):

    dataset_path = script_options['dataset_path']
    current_path = os.path.dirname(os.path.realpath(__file__))
    files_list   = []

    try:
        os.chdir(dataset_path)
        proc = subprocess.Popen(
            " git annex find --include='*' .",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        output, error = proc.communicate()
        files_list = output.decode().split("\n")
    except Exception:
        traceback.print_exc()
        sys.exit()
    finally:
        os.chdir(current_path)

    return files_list


def get_files_and_urls(script_options, annex):

    dataset_path = script_options['dataset_path']
    current_path = os.path.dirname(os.path.realpath(__file__))

    results = {}
    try:
        os.chdir(dataset_path)
        annex_results = annex("whereis", ".", "--json")
        results_list  = annex_results.split("\n")
        for annex_result_item in results_list:
            r_json = json.loads(annex_result_item)
            file_path = r_json['file']
            file_urls = []
            for entry in r_json['whereis']:
                file_urls.extend(entry['urls'])
            results[file_path] = file_urls
    except Exception:
        traceback.print_exc()
        sys.exit()
    finally:
        os.chdir(current_path)

    return results


def filter_invalid_urls(files_and_urls_dict, regex_pattern):

    filtered_dict = {}
    for file_path in files_and_urls_dict.keys():
        filtered_urls_list = filter(
            lambda x: re.search(regex_pattern, x),
            files_and_urls_dict[file_path]
        )
        filtered_dict[file_path] = filtered_urls_list

    return filtered_dict


def remove_url(filtered_file_urls_dict, script_options, annex):

    dataset_path = script_options['dataset_path']
    current_path = os.path.dirname(os.path.realpath(__file__))


    try:
        os.chdir(dataset_path)
        for file_path in filtered_file_urls_dict.keys():
            for url in filtered_file_urls_dict[file_path]:
                if script_options['run_removal']:
                    annex('rmurl', file_path, url)
                else:
                    print(
                        f"\nWill be running `git annex rmurl {file_path} {url}`\n"
                    )
    except Exception:
        traceback.print_exc()
    finally:
        os.chdir(current_path)


if __name__ == "__main__":
    main(sys.argv[1:])