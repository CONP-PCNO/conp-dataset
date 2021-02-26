import getopt
from sys import argv
from datetime import date
import json
from functions import aggregate, normalize_and_count


def main(argv):
    timestamp = date.today()
    opts, args = getopt.getopt(argv, "", ["filename=", "privacy=", "types=", "licenses=",
                                          "is_about=", "formats=", "keywords="])

    options = dict(privacy=True, types=True, licenses=True, is_about=True, formats=True, keywords=True)
    filename = f"report_{timestamp}"

    for opt, arg in opts:
        for op in ["privacy", "types", "licenses", "is_about", "formats", "keywords"]:
            if opt == str("--" + op) and arg == "False":
                options[op] = False
            elif opt == '--filename':
                filename = arg

    report = aggregate(
        privacy=options["privacy"],
        types=options["types"],
        licenses=options["licenses"],
        is_about=options["is_about"],
        formats=options["formats"],
        keywords=options["keywords"]
    )
    # create file with duplicate terms
    normalize_and_count(report)
    # save report to a file
    with open(f"{filename}.json", "w") as report_file:
        json.dump(report, report_file, indent=4)
        print("Report created.")


def info():
    print("Usage:"
          "python report_generator.py [--privacy=False --types=False --licenses=False "
          "--is_about= --formats=False --keywords=False]")
    return


if __name__ == "__main__":
    main(argv[1:])
