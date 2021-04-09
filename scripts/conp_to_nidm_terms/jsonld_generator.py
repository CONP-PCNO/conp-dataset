import getopt
from sys import argv

from functions import API_KEY
from functions import collect_values
from functions import generate_jsonld_files


def main(argv):
    opts, args = getopt.getopt(
        argv,
        "",
        [
            "privacy=",
            "types=",
            "licenses=",
            "is_about=",
            "formats=",
            "keywords=",
            "use_api=",
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
    use_api = True

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
        elif opt == "--use_api" and arg == "False":
            use_api = False
        else:
            help_info()
            exit()

    if use_api and not API_KEY:
        print(
            "The API key is not set in the api_key.json. Add your API Key or set --use_api=False",
        )
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

    generate_jsonld_files(report=report, use_api=use_api)


def help_info():
    print(
        "Usage:"
        "python jsonld_generator.py [--privacy=False --types=False --licenses=False "
        "--is_about= --formats=False --keywords=False --use_api=False --help]",
    )


if __name__ == "__main__":
    main(argv[1:])
