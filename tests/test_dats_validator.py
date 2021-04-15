import copy
import json
import os
import unittest

from scripts.dats_validator.validator import REQUIRED_EXTRA_PROPERTIES
from scripts.dats_validator.validator import validate_extra_properties
from scripts.dats_validator.validator import validate_json
from scripts.dats_validator.validator import validate_non_schema_required

EXAMPLES = os.path.join(os.getcwd(), "scripts", "dats_validator", "examples")
VALID = os.path.join(EXAMPLES, "valid_dats.json")
INVALID = os.path.join(EXAMPLES, "invalid_dats.json")


with open(VALID) as v_file:
    valid_obj = json.load(v_file)

with open(INVALID) as inv_file:
    invalid_obj = json.load(inv_file)


class JsonschemaTest(unittest.TestCase):
    def test_validate_json(self):
        valid_validation = validate_json(valid_obj)
        invalid_validation = validate_json(invalid_obj)
        self.assertEqual(valid_validation, True)
        self.assertEqual(invalid_validation, False)


class ExtraPropertiesTest(unittest.TestCase):
    def test_non_schema_required(self):
        valid_validation, errors = validate_non_schema_required(valid_obj)
        invalid_validation, errors = validate_non_schema_required(invalid_obj)
        self.assertEqual(valid_validation, True)
        self.assertEqual(invalid_validation, False)

    def test_exception(self):
        modified_copy = copy.deepcopy(valid_obj)
        # two possible key errors are extraProperties and title (the latter since it's used in error message)
        # introduce key error
        del modified_copy["extraProperties"]
        with self.assertRaises(Exception):
            validate_non_schema_required(modified_copy)

        modified_copy_2 = copy.deepcopy(valid_obj)
        for child in modified_copy_2["hasPart"]:
            # KeyError on 'title' will only be raised if there is an error in extraProperties
            del child["title"]
            del child["extraProperties"][1]
        with self.assertRaises(Exception):
            validate_non_schema_required(modified_copy_2)

    def test_conp_status_values(self):
        modified_copy = copy.deepcopy(valid_obj)
        for prop in modified_copy["extraProperties"]:
            if prop["category"] == "CONP_status":
                prop["values"] = [
                    {"value": "conp"},
                    {"value": "External"},
                    {"value": "random"},
                    {"value": "canadian"},
                ]
        invalid_validation, errors = validate_extra_properties(modified_copy)
        for error in errors:
            self.assertIn(
                f"Allowed values are {REQUIRED_EXTRA_PROPERTIES['CONP_status']}",
                error,
            )

    def test_subject(self):
        modified_copy = copy.deepcopy(valid_obj)
        for prop in modified_copy["extraProperties"]:
            if prop["category"] in REQUIRED_EXTRA_PROPERTIES.keys():
                del prop
        invalid_validation, errors = validate_extra_properties(modified_copy)
        for error in errors:
            self.assertIn("required but not found", error)


if __name__ == "__main__":
    unittest.main()
