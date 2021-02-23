import getopt
from sys import argv
from functions import generate_term_files, aggregate


def main(argv):
    opts, args = getopt.getopt(argv, "", ["privacy=", "types=", "licenses=",
                                          "is_about=", "formats=", "keywords="])

    options = dict(privacy=True, types=True, licenses=True, is_about=True, formats=True, keywords=True)

    for opt, arg in opts:
        for op in ["privacy", "types", "licenses", "is_about", "formats", "keywords"]:
            if opt == str("--" + op) and arg == "False":
                options[op] = False
            else:
                info()

    report = aggregate(
        privacy=options["privacy"],
        types=options["types"],
        licenses=options["licenses"],
        is_about=options["is_about"],
        formats=options["formats"],
        keywords=options["keywords"]
    )
    generate_term_files(report)


def info():
    print("Usage:"
          "python jsonld_generator.py [--privacy=False --types=False --licenses=False "
          "--is_about= --formats=False --keywords=False]")
    return


if __name__ == "__main__":
    main(argv[1:])
