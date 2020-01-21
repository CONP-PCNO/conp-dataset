import unittest
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'scripts'))
from dats_validator.validator import validate_json


EXAMPLES = os.path.join(os.path.dirname(sys.path[0]), 'scripts', 'dats_validator', 'examples')

class JsonschemaTest(unittest.TestCase):
    valid =  os.path.join(EXAMPLES, 'valid_dats.json')
    invalid = os.path.join(EXAMPLES, 'invalid_dats.json')

    def test_validate_json(self):
        with open(self.valid) as v_file:
            valid_obj = json.load(v_file)
            valid_validation = validate_json(valid_obj)
        with open(self.invalid) as inv_file:
            invalid_obj = json.load(inv_file)
            invalid_validation = validate_json(invalid_obj)
        self.assertEqual(valid_validation, True)
        self.assertEqual(invalid_validation, False)


if __name__ == '__main__':
    unittest.main()
