# Developing repository scripts

## Structure

- `Crawlers/` contains the shared crawler workflow and OSF/Zenodo providers.
- `dats_validator/`, `dats_jsonld_annotator/`, `DATS2csv/`, and
  `conp_to_nidm_terms/` handle DATS validation, annotation, export, and term
  reporting.
- `data_aggregation_summary_scripts/` contains dataset and tool CSV reports.
- `datalad_crawlers/`, `datalad_helper_scripts/`, and `datalad_utils.py`
  provide DataLad and remote-file operations.
- Root-level scripts include crawler entry points, single-record importers,
  archival and unlock helpers, and the tracked-filename check.

## Safe development

Treat scripts that contact OSF, Zenodo, GitHub, FTP/SFTP, or NIF as network
clients. Crawler and import commands can download files, change a DataLad
dataset, and in some configurations push repository changes. `auto_archive.py`,
`unlock.py`, and the deprecated-URL helper also change local dataset or
Git-annex state. Check each command's arguments and side effects before use;
prefer temporary clones and disposable datasets for manual verification.

Do not put API keys or access tokens in source files or committed configuration.
Use the repository's approved local credential mechanism and avoid logging
secret-bearing URLs.

## Checks

Use the Python and development dependencies declared by the repository. Static
linting can be run with:

```bash
uv run ruff check scripts
```

The test suite includes crawler and metadata checks. Consult the repository
test documentation before running it because some tests may require external
tools, schemas, datasets, or credentials. Prefer focused tests and fixtures;
do not use production datasets for write-oriented checks.

For the state and maintenance assessment of each source file, see
[REPORT-SCRIPTS.md](REPORT-SCRIPTS.md).
