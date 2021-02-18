import os
import sys
import json
import logging
from collections import Counter
from copy import deepcopy
import requests


logger = logging.getLogger(__name__)

CONP_DATASET_ROOT = sys.path[1]
PROJECTS = os.path.join(CONP_DATASET_ROOT, "projects")
PWD = os.path.dirname(os.path.realpath(__file__))

# More about NIF API endpoints https://neuinfo.org/about/webservices
NIF_API_URL = "https://scicrunch.org/api/1/ilx/search/term/"

# Load jsonld template
with open("template.jsonld", "r", encoding="utf-8") as template_file:
    JSONLD_TEMPLATE = json.load(template_file)


def _raise_error(er): raise Exception(er)


def get_api_response(term):
    """ Call NIF API and retrieve InterLex URI for a term. """

    # API Key must be provided
    with open("api_key.json", "r", encoding="utf-8") as api_key_file:
        api_key_json = json.load(api_key_file)
        key = api_key_json["api_key"] if api_key_json["api_key"] != "" else _raise_error(f"{api_key_json['_comment']}")

    try:
        api_key = f"?key={key}"
        r = requests.get(NIF_API_URL + term + api_key, headers={'accept': 'application/json'})
        r.raise_for_status()
        response = json.loads(r.content.decode('utf-8'))
        match = str()
        # Standard response will have existing_ids key
        if response["data"]["existing_ids"]:
            for i in response["data"]["existing_ids"]:
                match = i["iri"] if "curie" in i and "ILX:".upper() in i["curie"] else match
        else:
            match = "no match found"
        return match

    except requests.exceptions.HTTPError as e:
        logger.error(f"Error: {e}")


def aggregate(privacy=True, types=True, licenses=True, is_about=True, formats=True, keywords=True):
    """
    Iterates over projects directory retrieving DATS file for each project.
    Aggregates all values and their count for selected properties in the report object.
    """

    # Text values to aggregate
    privacy_values = set()
    licenses_values = set()
    types_datatype_values = set()
    is_about_values = set()
    distributions_formats = set()
    keywords_values = set()

    dats_files_count = 0

    # Access DATS.json in each project's root directory
    for path, directories, files in os.walk(PROJECTS):
        if "DATS.json" in files:
            dats_files_count += 1
            dats_file = os.path.join(path, "DATS.json")
            with open(dats_file, "r", encoding="utf-8") as json_file:
                dats_data = json.load(json_file)

                # privacy is not required
                if privacy and "privacy" in dats_data:
                    privacy_values.add(dats_data["privacy"])

                if types:
                    # types are required
                    for typ in dats_data["types"]:
                        # types takes four possible datatype schemas
                        datatype_schemas = ["information", "method", "platform", "instrument"]
                        types_datatype_values.update(set(typ[t]["value"] for t in datatype_schemas if t in typ))

                if licenses:
                    # licenses is required
                    licenses_values.update(set(l["name"] for l in dats_data["licenses"]))

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
                            distributions_formats.update(set(f for f in dist["formats"]))

                if keywords:
                    keywords_values.update(set(k["value"] for k in dats_data["keywords"]))

    # report = dict(dats_files_processed=dats_files_count)
    report = dict()
    for key, value in zip(["privacy", "licenses", "types", "is_about", "formats", "keywords"],
                          [privacy_values, licenses_values, types_datatype_values, is_about_values,
                           distributions_formats, keywords_values]):
        if value:
            report[key] = {
                "count": len(value),
                "values": list(value)
            }
    return report


def normalize_and_count(report):
    errors = list()
    for key in ["privacy", "licenses", "types", "is_about", "formats", "keywords"]:
        if key in report:
            terms = report[key]["values"]
            normilized_terms = dict()
            for term in terms:
                if term.lower() in normilized_terms:
                    normilized_terms[term.lower()].append(term)
                else:
                    normilized_terms[term.lower()] = [term]

            if report[key]["count"] == len(normilized_terms.keys()):
                logger.info(f"All terms are unique in {key}.")
            else:
                for k, v in normilized_terms.items():
                    if len(v) > 1:
                        errors.append(f"{key.title()} duplicate terms: {v}")
    with open('duplicates.txt', 'w') as f:
        for i, item in enumerate(errors, 1):
            f.write(f"{i}. {item}\n")
    return errors


def generate_term_files(report):
    """
    Generates a jsonld file for each unique term.
    Files are saved to the directories respectively to their properties.
    """
    terms_counter = Counter()
    for key, value in report.items():
        for term in value["values"]:
            terms_counter.update((term.lower(),))
            jsonld_description = deepcopy(JSONLD_TEMPLATE)
            jsonld_description["label"] = f"{term.lower()}"
            # Get NIF API matching URI
            jsonld_description["sameAs"] = get_api_response(term.lower())
            # Create a folder for each text value type (e.g. privacy, licenses, etc.)
            if not os.path.exists(os.path.join(PWD, key)):
                os.makedirs(os.path.join(PWD, key))
            filename = "".join(x for x in term.title().replace(" ", "") if x.isalnum())
            # Create and save jsonld file in a respestive folder
            with open(f"{os.path.join(PWD, key, filename)}.jsonld", "w", encoding="utf-8") as jsonld_file:
                json.dump(jsonld_description, jsonld_file, indent=4, ensure_ascii=False)

    return f"Created {len(terms_counter.keys())} jsonld files."
