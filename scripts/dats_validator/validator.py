import jsonschema
import os
import json
import logging
import getopt
from sys import argv


logger = logging.getLogger(__name__)
# path to a top-level schema
SCHEMA_PATH = os.path.dirname(os.path.realpath(__file__)) + '/conp-dats/dataset_schema.json'

def main(argv):
    FORMAT = '%(message)s'
    logging.basicConfig(format=FORMAT)
    logging.getLogger().setLevel(logging.INFO)
    opts, args = getopt.getopt(argv, "", ["file="])
    json_filename = ''

    for opt, arg in opts:
        if opt == '--file':
            json_filename = arg

    if json_filename == '':
        help()
        exit()

    with open(json_filename) as json_file:
        json_obj = json.load(json_file)
        validate_json(json_obj)


def validate_json(json_obj):
    with open(SCHEMA_PATH) as s:
        json_schema = json.load(s)
    # first validate schema file
    v = jsonschema.Draft4Validator(json_schema)
    # now validate json file
    try:
        jsonschema.validate(json_obj, json_schema, format_checker=jsonschema.FormatChecker())
        logger.info('The file is valid. Validation passed.')
        return True
    except jsonschema.exceptions.ValidationError:
        errors = [e for e in v.iter_errors((json_obj))]
        logger.info(f"The file is not valid. Total errors: {len(errors)}")
        for i, error in enumerate(errors, 1):
            logger.error(f"{i} Validation error in {'.'.join(str(v) for v in error.path)}: {error.message}")
        logger.info('Validation failed.')
        return False


def help():
    return logger.info('Usage: python validator.py --file=doc.json')


if __name__ == "__main__":
    main(argv[1:])
