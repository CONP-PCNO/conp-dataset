import argparse
import json
import logging
import pathlib as pal
import sys
import time

import jsonschema as jss


CONTEXT_DIR = (pal.Path(__file__).parent / "context" / "sdo").resolve()
SCHEMA_DIR = (pal.Path(__file__).parent / "schema").resolve()
logger = logging.getLogger("DATS annotator")


def find_schema(parent_schema, term, json_object):
    """
    This function finds the appropriate JSON schema for a term in a DATS JSON object. To do
    so, it relies on the JSON schema of the supplied JSON object.

    :param parent_schema: The DATS JSON schema that corresponds to the json_object parameter
    :param term: the string term for which the schema shall be found
    :param json_object: the JSON object that contains the term and to which the parent_schema corresponds to
    :return: the DATS JSON schema for the term
    """
    ps = parent_schema["properties"]
    if term not in ps.keys():
        # The only way this could happen on a valid dataset is if someone has specified additional properties
        # We'd like to discourage this
        logger.warning(
            f'I cannot find {term = } in the parent schema: {parent_schema["id"]}.\n{json_object = }'
        )
        return None

    # Set up the schema resolver
    resolver = jss.RefResolver(base_uri=parent_schema["id"], referrer=None)

    # See if "items" is in the schema entry
    search_dict = ps[term]
    if "items" in search_dict.keys():
        search_dict = ps[term]["items"]

    # This section is looking for the name of the DATS schema that should be applied to the term
    # If there are multiple possibilities (e.g. "anyOf", "oneOf", "allOf") we want to pick a schema
    # for which the current term value validates
    if "$ref" in search_dict.keys():
        # There is only one possible schema
        schema_name = search_dict["$ref"]
    elif len(set(search_dict.keys()).intersection(["anyOf", "oneOf", "allOf"])) > 0:
        # There is (most likely) more than one option for the schema as indicated by one of the
        # keys from ["anyOf", "oneOf", "allOf"]
        schema_rel = list(
            set(search_dict.keys()).intersection(["anyOf", "oneOf", "allOf"])
        )[0]
        possible_schemata = []
        # We will now iterate over the possible schemata for the term
        for ref in search_dict[schema_rel]:
            # Get the schema
            ref_name = ref["$ref"]
            _schema_uri, _schema = resolver.resolve(ref_name)
            if _schema_uri == resolver.base_uri:
                _schema = parent_schema
            if jss.Draft4Validator(_schema).is_valid(json_object):
                # If the schema validates the term value (json_object) then we can keep
                # it around as a potential schema
                possible_schemata.append(ref_name)
        if len(possible_schemata) > 1:
            # TODO: decide if we let the user pick which option to go with
            logger.debug(f"I got more than one option for {term}: {possible_schemata}")
        elif len(possible_schemata) == 0:
            logger.warning(
                f"I have no fitting schema for {json_object} {term} among {search_dict[schema_rel]}"
            )
            return None
        # If anything fits, just pick the first one
        # TODO: we may want to leave this up to the user here, particularly if the instances
        #       map to different / meaningful things in SDO
        schema_name = possible_schemata[0]
    else:
        # There is nothing to be done here in terms of annotation
        logger.info(f"{term = } does not need to be annotated")
        return None

    _schema_uri, _schema = resolver.resolve(schema_name)
    if _schema_uri == resolver.base_uri:
        _schema = parent_schema
    if _schema is None:
        logger.warning(
            f'The schema we found for {schema_name}: was None! The parent schema was: {parent_schema["id"]}'
            f"and it was resolved using this URI: {resolver.base_uri}"
        )
    return _schema


def find_context(schema_id, context_dir):
    """
    For a given DATS JSON schema, finds and loads the corresponding DATS SDO context file.
    This function makes use of the fact that DATS SDO context files follow a similar naming structure
    to the DATS JSON schema files.

    :param schema_id: the string URI of the schema
    :param context_dir: the directory path where the DATS SDO context files can be found
    :return: the @context section of the DATS SDO context file as a dictionary
    """
    schema_name = pal.Path(schema_id).name
    context_name = pal.Path(schema_name.replace("_schema", "_sdo_context")).with_suffix(
        ".jsonld"
    )
    context = json.load(open(context_dir / context_name))["@context"]
    return context


def annotate_dats_object(
    json_object, schema, specific_context, context_dir=CONTEXT_DIR
):
    """
    This function recursively traverses a DATS instance and generates two things:

    1. The @type declarations for each node in the JSONLD graph
    2. A copy of the specific context mappings needed to map the DATS instance to SDO

    :param json_object: A DATS instance as a dictionary
    :param schema: The DATS JSON schema corresponding to the json_object as a dictionary
    :param specific_context:  the DATS instance specific context
    :param context_dir: the path to the DATS context files
    :return: The DATS instance with appropriate @type declarations, and the DATS instance specific context
    """

    if not isinstance(json_object, dict) or schema is None:
        # If the json_object is not a dict, then it cannot be annotated
        # If the schema is None, then the key might not be part of the DATS schema
        return json_object, specific_context

    context = find_context(schema["id"], context_dir)
    for k, v in json_object.items():
        if isinstance(v, dict):
            _schema = find_schema(schema, k, v)
            json_object[k], _local_context = annotate_dats_object(
                v, _schema, specific_context, context_dir
            )
            specific_context.update(_local_context)
        if isinstance(v, list):
            # Let's find the schema link under "items"
            annotation_list = []
            for vv in v:
                if not isinstance(vv, dict):
                    annotation_list.append(vv)
                    continue
                _schema = find_schema(schema, k, vv)
                _json_o, _local_context = annotate_dats_object(
                    vv, _schema, specific_context, context_dir
                )
                annotation_list.append(_json_o)
                specific_context.update(_local_context)
            json_object[k] = annotation_list
        # Add the key mapping to the context
        if k not in context.keys():
            logger.debug(f'{k} not in context: {pal.Path(schema["id"]).name}')
            continue
        if k not in specific_context.keys():
            specific_context[k] = context[k]
            logger.debug(f"{k} added to context: {context[k]}")
        elif specific_context[k] == context[k]:
            continue
        else:
            logger.debug(f"{k} duplicate: {specific_context[k]} vs {context[k]}")
            continue

    dtype = schema["properties"]["@type"]["enum"][0]
    if dtype not in context.keys():
        logger.debug(f'{dtype} not in context {schema["id"]}')
    else:
        specific_context[dtype] = context[dtype]
    json_object["@type"] = dtype
    return json_object, specific_context


def gen_jsonld_outpath(dats_json_f, out_path):
    """
    This function generates an output file path for the annotated DATS JSONLD file.

    :param dats_json_f: the path to the original DATS instance file
    :param out_path: the folder or new file path where the annotated DATS.jsonld file should be stored
    :return:  the final DATS.jsonld file path
    """
    if not isinstance(dats_json_f, pal.Path):
        dats_json_f = pal.Path(dats_json_f)
    if out_path is not None and not isinstance(out_path, pal.Path):
        out_path = pal.Path(out_path)

    out_name = dats_json_f.with_suffix(".jsonld").name
    if out_path is None:
        # We save the output to the parent directory of the current DATS JSON file
        out_path = dats_json_f.parent
    elif out_path.suffix != "":
        # We have most likely gotten a path to a non-existent file, let's use that
        return out_path
    elif not out_path == dats_json_f.parent:
        # We are saving this somewhere other than the original folder
        out_name = f"{dats_json_f.parent.name}_{out_name}"
    if out_path.is_dir():
        dats_jsonld_f = out_path / out_name
    else:
        raise Exception(
            f"{out_path = } for {dats_json_f.resolve()} is not a path to a file or directory. "
            f"I don't know where to store the output. "
            f"Please provide a valid path with the --out flag."
        )
    return dats_jsonld_f


def dats_to_jsonld(dats_f, schema_f, context_dir, out_path=None, clobber=False):
    """
    Helper function to load the inputs and store the annotated DATS.jsonld file
    """
    # TODO: log how many terms were not annotated because they are missing from context
    tic = time.time()
    dats_jsonld_f = gen_jsonld_outpath(dats_f, out_path)
    if dats_jsonld_f.is_file():
        if clobber:
            logger.warning(
                f"{dats_jsonld_f.resolve()} already exists and {clobber = }. "
                f"The file {dats_jsonld_f.resolve()} will be overwritten now!"
            )
        else:
            logger.warning(
                f"{dats_jsonld_f.resolve()} already exists and {clobber = }. "
                f"Consider setting the clobber flag to overwrite existing files"
            )
            return

    dats_json = json.load(open(dats_f))
    schema = json.load(open(schema_f))

    # Do a very basic validation of the JSON object before we try to annotate it
    if not jss.Draft4Validator(schema).is_valid(dats_json):
        logger.error(
            f"{dats_f.resolve()} is not a valid DATS file. "
            f"If you think this should be a valid DATS file, "
            f"please use the CONP validator to get a list of specific errors."
            f"\n\nSkipping this file."
        )
        return

    # Now do the annotation
    try:
        dats_jsonld, context = annotate_dats_object(dats_json, schema, {}, context_dir)
    except Exception as e:
        logger.exception(f"Annotating {dats_f} did not complete!", e, exc_info=True)

    # Prefill the context with the SDO mapping
    context["sdo"] = "https://schema.org/"
    # Combine the context and the dats graph
    dats_jsonld["@context"] = [
        context,
    ]
    logger.info(
        f"Final result written to {dats_jsonld_f.resolve()}! This took {time.time()-tic :.2f} seconds"
    )
    json.dump(dats_jsonld, open(dats_jsonld_f, "w"), indent=2)


def main(cli_args):

    logging.basicConfig(format="%(levelname)s:  %(message)s", level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Annotate a DATS.json file to DATS.jsonld given a schema"
    )
    parser.add_argument(
        "dats_path",
        type=pal.Path,
        help="""
                If this is a path to a DATS file, then only this DATS file will be annotated.
                If this is a path to a directory, then each subdirectory of this directory is expected
                to contain a DATS file called DATS.json. Each of these files will then be annotated iteratively
                """,
    )
    parser.add_argument(
        "-ds",
        "--dats_schema",
        type=pal.Path,
        default=SCHEMA_DIR / "dataset_schema.json",
        help="""Specify the full path to a DATS dataset schema file if you don't want to use the default one""",
    )
    parser.add_argument("-dc", "--dats_context_dir", type=pal.Path, default=CONTEXT_DIR)
    parser.add_argument(
        "--out",
        type=pal.Path,
        default=None,
        help="Where to create the JSONLD file(s) (default = in the same folder).",
    )
    parser.add_argument("--clobber", action="store_true")
    args = parser.parse_args(cli_args)

    if args.dats_path.is_file():
        dats_to_jsonld(
            dats_f=args.dats_path,
            schema_f=args.dats_schema,
            context_dir=args.dats_context_dir,
            out_path=args.out,
            clobber=args.clobber,
        )
    elif args.dats_path.is_dir():
        files_to_convert = list(args.dats_path.glob("*/DATS.json"))
        if not args.out.is_dir():
            logger.warning(
                f"The {args.out.resolve()} folder will be created and JSONLD files will be saved in it."
            )
            args.out.mkdir()
        if files_to_convert is None:
            logger.error(
                f"could not find any DATS.json files in subdirectories of {args.dats_path.resolve()}"
            )
            exit(code=1)

        logger.info(
            f"Found {len(files_to_convert)} files to convert at {args.dats_path.resolve()}"
        )
        start = time.time()
        for file_idx, dats_f in enumerate(files_to_convert, start=1):
            logger.info(
                f"Now processing file {file_idx}/{len(files_to_convert)}: {dats_f.parent.name}"
            )
            dats_to_jsonld(
                dats_f=dats_f,
                schema_f=args.dats_schema,
                context_dir=args.dats_context_dir,
                out_path=args.out,
                clobber=args.clobber,
            )
        logger.info(
            f"Completed annotating {len(files_to_convert)} DATS files. "
            f"This took {time.time()-start :.2f} seconds."
        )
    else:
        logger.error(f"I cannot find {args.dats_path}. Will stop now.")


if __name__ == "__main__":
    main(sys.argv[1:])
