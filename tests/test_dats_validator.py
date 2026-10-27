import copy
import json
import os
import unittest

from scripts.dats_validator.validator import REQUIRED_EXTRA_PROPERTIES
from scripts.dats_validator.validator import validate_access_urls
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
        with self.assertRaises(KeyError):
            validate_non_schema_required(modified_copy)

        modified_copy_2 = copy.deepcopy(valid_obj)
        for child in modified_copy_2["hasPart"]:
            # KeyError on 'title' will only be raised if there is an error in extraProperties
            del child["title"]
            del child["extraProperties"][1]
        with self.assertRaises(KeyError):
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


def _record(*distributions):
    return {"title": "t", "distributions": list(distributions)}


def _dist(landing, url, identifier=None):
    dist = {"access": {"landingPage": landing, "accessURL": url}}
    if identifier:
        dist["identifier"] = {"identifier": identifier, "identifierSource": "OSF"}
    return dist


ZIP = "https://files.us.osf.io/v1/resources/{}/providers/{}/?zip="


class AccessURLTest(unittest.TestCase):
    def test_osf_link_to_another_project(self):
        # the January 2026 links: OSF ignores the value after zip=, so this is znt9d
        bad = _record(
            _dist(
                "https://osf.io/q482e",
                "https://files.us.osf.io/v1/resources/znt9d/providers/osfstorage/?zip=q482e",
            ),
        )
        valid, errors = validate_access_urls(bad)
        self.assertFalse(valid)
        self.assertIn("znt9d", errors[0])

    def test_osf_own_project_and_named_component(self):
        own = _record(_dist("https://osf.io/q482e", ZIP.format("q482e", "osfstorage")))
        self.assertTrue(validate_access_urls(own)[0])
        part = _record(
            _dist(
                "https://osf.io/xwajn/",
                ZIP.format("qzucv", "osfstorage"),
                "https://osf.io/qzucv/",
            ),
        )
        self.assertTrue(validate_access_urls(part)[0])

    def test_osf_zip_value_and_addon(self):
        valued = _record(
            _dist(
                "https://osf.io/znt9d",
                "https://files.us.osf.io/v1/resources/znt9d/providers/osfstorage/?zip=znt9d",
            ),
        )
        self.assertFalse(validate_access_urls(valued)[0])
        addon = _record(_dist("https://osf.io/4dgby", ZIP.format("4dgby", "github")))
        valid, errors = validate_access_urls(addon)
        self.assertFalse(valid)
        self.assertIn("add-on", errors[0])

    def test_zenodo(self):
        other = _record(
            _dist(
                "https://zenodo.org/records/1",
                "https://zenodo.org/records/2/files/a.zip/content",
            ),
        )
        self.assertFalse(validate_access_urls(other)[0])
        archive = _record(
            _dist(
                "https://zenodo.org/records/1",
                "https://zenodo.org/api/records/1/files-archive",
            ),
        )
        self.assertFalse(validate_access_urls(archive)[0])
        own = _record(
            _dist(
                "https://zenodo.org/records/1",
                "https://zenodo.org/records/1/files/a.zip/content",
            ),
        )
        self.assertTrue(validate_access_urls(own)[0])

    def test_no_access_url_and_github_archive(self):
        self.assertTrue(validate_access_urls(_record({"access": {"landingPage": "x"}}))[0])
        github = _record(
            _dist(
                "https://osf.io/6ctsj",
                "https://github.com/a/b/archive/refs/heads/main.zip",
            ),
        )
        self.assertTrue(validate_access_urls(github)[0])
