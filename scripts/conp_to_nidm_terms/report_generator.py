import getopt
import json
from datetime import date
from sys import argv

from functions import collect_values
from functions import find_duplicates


def main(argv):
    timestamp = date.today()
    opts, args = getopt.getopt(
        argv,
        "",
        [
            "filename=",
            "privacy=",
            "types=",
            "licenses=",
            "is_about=",
            "formats=",
            "keywords=",
            "help",
        ],
    )

    options = dict(
        privacy=True,
        types=True,
        licenses=True,
        is_about=True,
        formats=True,
        keywords=True,
    )
    filename = f"report_{timestamp}"

    for opt, arg in opts:
        opt_properties = [
            "--privacy",
            "--types",
            "--licenses",
            "--is_about",
            "--formats",
            "--keywords",
        ]
        if opt in opt_properties and arg == "False":
            options[opt.replace("--", "")] = False
        elif opt == "--filename":
            filename = arg
        else:
            help_info()
            exit()

    report, dats_files_count = collect_values(
        privacy=options["privacy"],
        types=options["types"],
        licenses=options["licenses"],
        is_about=options["is_about"],
        formats=options["formats"],
        keywords=options["keywords"],
    )
    print(f"DATS files processed: {dats_files_count}")
    # check if duplicate terms exist
    duplicates = find_duplicates(report)
    if duplicates:
        # save duplicates to a file
        with open("duplicates.txt", "w") as f:
            for i, item in enumerate(duplicates, 1):
                f.write(f"{i}. {item}\n")
            print("Duplicates were found and saved to the duplicates.txt.")
    # save report to a file
    with open(f"{filename}.json", "w") as report_file:
        json.dump(report, report_file, indent=4)
        print(f"Report {filename}.json created.")


def help_info():
    print(
        "Usage:"
        "python report_generator.py [--privacy=False --types=False --licenses=False "
        "--is_about= --formats=False --keywords=False --help]",
    )


if __name__ == "__main__":
    main(argv[1:])
