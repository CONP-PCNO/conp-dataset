# DATS JSONLD annotator


This is a command line tool to turn a [DATS.json file](https://github.com/datatagsuite) into a DATS.jsonld file with the appropriate `@type` declarations and the
[schema.org](https://schema.org/) `@context` mapping needed for this specific file. To do this, the tool relies on the [CONP specific DATS-schema files](https://github.com/CONP-PCNO/schema) and
the [CONP specific DATS-SDO-context files](https://github.com/CONP-PCNO/context).

## Usage

There are two main options:

**Option 1**:

Annotate all files called `DATS.json` in the subdirectories of a directory.

```shell
python annotator.py /path/to/project/folder --out /path/to/output/directory
```

The `--out` parameter is optional, if it is not specified, the files will be generated in the
same directory as the original DATS.json.

**Option 2**:
Annotate a single DATS file
```shell
python annotator.py /path/to/a/DATS_file.json --out /outputpath
```

The `--out` parameter can either be a file name or a directory.
