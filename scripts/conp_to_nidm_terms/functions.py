import json
import logging
import os
from collections import Counter
from copy import deepcopy

import requests


logger = logging.getLogger(__name__)


CONP_DATASET_ROOT_DIR = os.path.abspath(os.path.join(__file__, "../../.."))
# conp-dataset/projects
PROJECTS_DIR = os.path.join(CONP_DATASET_ROOT_DIR, "projects")
CURRENT_WORKING_DIR = os.path.dirname(os.path.realpath(__file__))

# More about NIF API endpoints https://neuinfo.org/about/webservices
NIF_API_URL = "https://scicrunch.org/api/1/ilx/search/term/"

# Load JSON-LD template
with open("template.jsonld", encoding="utf-8") as template_file:
    JSONLD_TEMPLATE = json.load(template_file)


# Set API key
with open("api_key.json", encoding="utf-8") as api_key_file:
    API_KEY = json.load(api_key_file)["api_key"]


def get_api_response(term):
    """
    Call NIF API and retrieve InterLex URI for a term.
    :param term: string with the term to send to the API
    :return: string Interlex URI
    """

    # API Key must be provided
    if not API_KEY:
        raise Exception(
            "Add your API Key for the NIF data services to the api_key.json file.",
        )

    try:
        api_key = f"?key={API_KEY}"
        r = requests.get(
            NIF_API_URL + term + api_key,
            headers={"accept": "application/json"},
        )
        r.raise_for_status()
        response = json.loads(r.content.decode("utf-8"))
        match = ""
        # Standard response will have existing_ids key
        if "existing_ids" in response["data"] and response["data"]["existing_ids"]:
            for i in response["data"]["existing_ids"]:
                # retrieve InterLex ID, its curie has "ILX" prefix
                match = (
                    i["iri"] if "curie" in i and "ILX:".upper() in i["curie"] else match
                )
        else:
            match = "no match found"
        return match

    except requests.exceptions.HTTPError as e:
        logger.error(f"Error: {e}")


def collect_values(
    privacy=True,
    types=True,
    licenses=True,
    is_about=True,
    formats=True,
    keywords=True,
):
    """
    Iterates over the projects directory content retrieving DATS file for each project.
    Aggregates all values and their count for selected properties in the report object.
    :param : set to False in order to exclude the property from the final report
    :return: dict object report, int how many DATS files were processed
    """

    # Text values to collect
    privacy_values = set()
    licenses_values = set()
    types_datatype_values = set()
    is_about_values = set()
    distributions_formats = set()
    keywords_values = set()

    dats_files_count = 0

    # Access DATS.json in each project's root directory
    for path, _, files in os.walk(PROJECTS_DIR):
        if "DATS.json" in files:
            dats_files_count += 1
            dats_file = os.path.join(path, "DATS.json")
            with open(dats_file, encoding="utf-8") as json_file:
                dats_data = json.load(json_file)

                # privacy is not required
                if privacy and "privacy" in dats_data:
                    privacy_values.add(dats_data["privacy"])

                if types:
                    # types are required
                    for typ in dats_data["types"]:
                        # types takes four possible datatype schemas
                        datatype_schemas = [
                            "information",
                            "method",
                            "platform",
                            "instrument",
                        ]
                        types_datatype_values.update(
                            {typ[t]["value"] for t in datatype_schemas if t in typ},
                        )

                if licenses:
                    # licenses is required
                    licenses_values.update(
                        {licence["name"] for licence in dats_data["licenses"]},
                    )

                # isAbout is not required
                if is_about and "isAbout" in dats_data:
                    for each_is_about in dats_data["isAbout"]:
                        if "name" in each_is_about:
                            is_about_values.add(each_is_about["name"])
                        elif "value" in each_is_about:
                            is_about_values.add(each_is_about["value"])
                        else:
                            pass

                # distributions is required
                if formats:
                    for dist in dats_data["distributions"]:
                        if "formats" in dist:
                            distributions_formats.update({f for f in dist["formats"]})

                if keywords:
                    keywords_values.update({k["value"] for k in dats_data["keywords"]})

    report = {}
    for key, value in zip(
        ["privacy", "licenses", "types", "is_about", "formats", "keywords"],
        [
            privacy_values,
            licenses_values,
            types_datatype_values,
            is_about_values,
            distributions_formats,
            keywords_values,
        ],
    ):
        if value:
            report[key] = {
                "count": len(value),
                "values": list(value),
            }
    return report, dats_files_count


def find_duplicates(report):
    """
    Finds duplicate values spelled in different cases (e.g. lowercase vs uppercase vs title)
    :param report: json object returned by collect_values()
    :return: list of errors describing where duplicates occur
    """
    errors = []
    for key in ["privacy", "licenses", "types", "is_about", "formats", "keywords"]:
        if key in report:
            terms = report[key]["values"]
            normilized_terms = {}
            for term in terms:
                if term.lower() in normilized_terms:
                    normilized_terms[term.lower()].append(term)
                else:
                    normilized_terms[term.lower()] = [term]

            if report[key]["count"] == len(normilized_terms.keys()):
                logger.info(f"All terms are unique in {key}.")
            else:
                for _, v in normilized_terms.items():
                    if len(v) > 1:
                        errors.append(f"{key.title()} duplicate terms: {v}")
    return errors


def generate_jsonld_files(report, use_api=True):
    """
    Generates a JSON-LD file for each unique term.
    Files are saved to the directories respective to their properties.
    :param report: json object returned by collect_values()
    :param use_api: defaults to True; if False then NIF API won't be called for InterLex match
    """
    terms_counter = Counter()
    for key, value in report.items():
        for term in value["values"]:
            terms_counter.update((term.lower(),))
            jsonld_description = deepcopy(JSONLD_TEMPLATE)
            jsonld_description["label"] = f"{term.lower()}"
            if use_api:
                # Get NIF API matching URI
                jsonld_description["sameAs"] = get_api_response(term.lower())
            # Create a folder for each text value type (e.g. privacy, licenses, etc.)
            if not os.path.exists(os.path.join(CURRENT_WORKING_DIR, key)):
                os.makedirs(os.path.join(CURRENT_WORKING_DIR, key))
            filename = "".join(x for x in term.title().replace(" ", "") if x.isalnum())
            # Create and save JSON-LD file in the respective folder
            with open(
                f"{os.path.join(CURRENT_WORKING_DIR, key, filename)}.jsonld",
                "w",
                encoding="utf-8",
            ) as jldfile:
                json.dump(jsonld_description, jldfile, indent=4, ensure_ascii=False)
    print(f"JSON-LD files created: {len(terms_counter.keys())}")
    return
