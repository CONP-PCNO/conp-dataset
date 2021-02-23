import getopt
from sys import argv
from datetime import date
import json
from generate_terms_jsonld import aggregate


def main(argv):
    timestamp = date.today()
    opts, args = getopt.getopt(argv, "", ["filename=", "privacy=", "types=", "licenses=",
                                          "is_about=", "formats=", "keywords="])
    filename = f"report_{timestamp}"
    privacy = True
    types = True
    licenses = True
    is_about = True
    formats = True
    keywords = True

    for opt, arg in opts:
        if opt == '--filename':
            filename = arg
        elif opt == '--privacy':
            privacy = arg
        elif opt == '--types':
            types = arg
        elif opt == '--licenses':
            licenses = arg
        elif opt == '--is_about':
            is_about = arg
        elif opt == '--keywords':
            keywords = arg
        elif opt == '--formats':
            formats = arg
        else:
            info()

    report = aggregate(privacy, types, licenses, is_about, formats, keywords)
    with open(f"{filename}.json", "w") as report_file:
        json.dump(report, report_file, indent=4)
        return f"Report created."


def info():
    print("Usage:"
          "python report_generator.py [--privacy=False --types=False --licenses=False "
          "--is_about= --formats=False --keywords=False]")
    return


if __name__ == "__main__":
    main(argv[1:])
