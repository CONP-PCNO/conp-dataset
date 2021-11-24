import json

import pytest

from scripts.dats_jsonld_annotator.annotator import annotate_dats_object
from scripts.dats_jsonld_annotator.annotator import CONTEXT_DIR
from scripts.dats_jsonld_annotator.annotator import find_context
from scripts.dats_jsonld_annotator.annotator import find_schema
from scripts.dats_jsonld_annotator.annotator import gen_jsonld_outpath
from scripts.dats_jsonld_annotator.annotator import SCHEMA_DIR


@pytest.fixture()
def basic_dats():
    return {"properties": {"my_term": {"bad_key": ""}}, "id": ""}


@pytest.fixture()
def dats_dataset_schema():
    return json.load(open(SCHEMA_DIR / "dataset_schema.json"))


@pytest.fixture()
def dats_person_schema():
    return json.load(open(SCHEMA_DIR / "person_schema.json"))


@pytest.fixture()
def basic_json():
    return {}


@pytest.fixture()
def dats_person_instance():
    return {"firstName": "Gustav", "lastName": "Gans"}


@pytest.fixture()
def dats_jsonld_person_instance():
    return {
        "jsonld": {"firstName": "Gustav", "lastName": "Gans", "@type": "Person"},
        "context": {
            "firstName": "sdo:givenName",
            "lastName": "sdo:familyName",
            "Person": "sdo:Person",
        },
    }


@pytest.fixture()
def dats_dataset_instance(dats_person_instance):
    return {
        "title": "",
        "types": {},
        "creators": dats_person_instance,
        "licenses": {"name": "license"},
        "description": "",
        "keywords": ["a", {"value": "word"}],
        "version": "",
        "distributions": {},
    }


@pytest.fixture()
def dats_jsonld_dataset_instance():
    return {
        "jsonld": {
            "title": "",
            "types": {"@type": "DataType"},
            "creators": {"firstName": "Gustav", "lastName": "Gans", "@type": "Person"},
            "licenses": {"name": "license", "@type": "License"},
            "description": "",
            "keywords": ["a", {"value": "word", "@type": "Annotation"}],
            "version": "",
            "distributions": {"@type": "DatasetDistribution"},
            "@type": "Dataset",
        },
        "context": {
            "title": {"@id": "sdo:name", "@type": "sdo:Text"},
            "DataType": "sdo:Thing",
            "firstName": "sdo:givenName",
            "lastName": "sdo:familyName",
            "Person": "sdo:Person",
            "creators": {"@id": "sdo:creator", "@type": "sdo:Thing"},
            "name": {"@id": "sdo:name", "@type": "sdo:Text"},
            "License": "sdo:CreativeWork",
            "licenses": "sdo:license",
            "description": {"@id": "sdo:description", "@type": "sdo:Text"},
            "value": {"@id": "sdo:value", "@type": "sdo:DataType"},
            "Annotation": "sdo:Thing",
            "DatasetDistribution": "sdo:DataDownload",
            "distributions": {"@id": "sdo:distribution", "@type": "sdo:DataDownload"},
            "Dataset": "sdo:Dataset",
            "keywords": {"@id": "sdo:keywords", "@type": "sdo:Thing"},
            "version": {"@id": "sdo:version", "@type": "sdo:Thing"},
            "types": {"@id": "sdo:identifier", "@type": "sdo:Thing"},
        },
    }


@pytest.fixture()
def dats_path(tmp_path):
    return tmp_path / "dats_root" / "DATS.json"


class TestFindSchema:
    def test_missing_term(self, basic_dats, basic_json):
        term = "missing_term"
        assert find_schema(basic_dats, term, basic_json) is None

    def test_bad_value(self, basic_dats, basic_json):
        term = "my_term"
        assert find_schema(basic_dats, term, basic_json) is None

    def test_term_with_a_single_possible_schema(self, dats_dataset_schema, basic_json):
        term = "identifier"
        test_schema = find_schema(dats_dataset_schema, term, basic_json)
        assert test_schema["id"].split("/")[-1] == "identifier_info_schema.json"

    def test_term_with_multiple_possible_schemata(
        self, dats_dataset_schema, dats_person_instance
    ):
        term = "creators"
        test_schema = find_schema(dats_dataset_schema, term, dats_person_instance)
        assert test_schema["id"].split("/")[-1] == "person_schema.json"

    def test_term_with_recursive_schema(
        self, dats_dataset_schema, dats_dataset_instance
    ):
        term = "hasPart"
        test_schema = find_schema(dats_dataset_schema, term, dats_dataset_instance)
        assert test_schema["id"].split("/")[-1] == "dataset_schema.json"


class TestFindContext:
    def test_find_dataset_context(self):
        schema_id = "/remote/dataset_schema.json"
        context = find_context(schema_id, CONTEXT_DIR)
        assert context.get("Dataset") == "sdo:Dataset"


class TestWalkSchema:
    def test_not_a_json_object(self, dats_dataset_schema):
        test_result = annotate_dats_object(
            None, dats_dataset_schema, {}, context_dir=CONTEXT_DIR
        )
        assert test_result == (None, {})

    def test_simple_instance(
        self, dats_person_schema, dats_person_instance, dats_jsonld_person_instance
    ):
        jsonld, context = annotate_dats_object(
            dats_person_instance, dats_person_schema, {}, context_dir=CONTEXT_DIR
        )
        assert jsonld == dats_jsonld_person_instance["jsonld"]
        assert context == dats_jsonld_person_instance["context"]

    def test_recursive_instance(
        self, dats_dataset_schema, dats_dataset_instance, dats_jsonld_dataset_instance
    ):
        jsonld, context = annotate_dats_object(
            dats_dataset_instance, dats_dataset_schema, {}, context_dir=CONTEXT_DIR
        )
        assert jsonld == dats_jsonld_dataset_instance["jsonld"]
        assert context == dats_jsonld_dataset_instance["context"]


class TestGenerateJsonldPath:
    def test_output_dir_does_exist(self, tmp_path, dats_path):
        out_path = tmp_path / "jsonld_out"
        out_path.mkdir()
        result_path = gen_jsonld_outpath(dats_path, out_path)
        assert result_path == out_path / "dats_root_DATS.jsonld"

    def test_output_dir_doesnt_exist(self, tmp_path, dats_path):
        # If the output dir does not exist when we call gen_jsonld_outpath
        # Then we want this to error out here
        # We only create output directories at the start
        out_path = tmp_path / "nonexistent"
        with pytest.raises(Exception):
            gen_jsonld_outpath(dats_path, out_path)

    def test_output_path_is_none(self, tmp_path, dats_path):
        dats_path.parent.mkdir()
        out_path = None
        result_path = gen_jsonld_outpath(dats_path, out_path)
        assert result_path == dats_path.parent / "DATS.jsonld"

    def test_paths_are_string(self, tmp_path, dats_path):
        out_path = tmp_path / "jsonld_out"
        out_path.mkdir()
        result_path = gen_jsonld_outpath(str(dats_path), str(out_path))
        assert result_path == out_path / "dats_root_DATS.jsonld"

    def test_output_is_file(self, tmp_path, dats_path):
        out_path = tmp_path / "output_here_please.jsonld"
        result_path = gen_jsonld_outpath(str(dats_path), str(out_path))
        assert result_path == out_path

    def test_output_dir_fails(self, tmp_path, dats_path):
        out_path = tmp_path / "some" / "arbitrary" / "path"
        with pytest.raises(Exception):
            gen_jsonld_outpath(dats_path, out_path)


class TestAnnotator:
    # TODO: write tests for the annotator function
    pass


class TestCLI:
    # TODO: write tests for the CLI parser
    pass
