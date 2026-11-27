# Repository scripts

This directory contains crawler jobs, dataset-maintenance commands, DATS tools,
and reporting utilities. Most commands operate on a DataLad dataset or write
files; review the target paths and credentials before running them.

## Find a tool

- **Crawling:** `crawl.py`, `crawl.sh`, and `Crawlers/` import OSF and Zenodo
  records into the CONP dataset. The scheduled shell wrapper can pull and push
  repository changes.
- **Single-record imports:** `import_single_osf_to_local_datalad.py` and
  `import_single_zenodo_to_local_datalad.py` create or update one local dataset.
  See [example invocations](how_to_use_import_single_scripts.md).
- **DataLad maintenance:** `auto_archive.py`, `unlock.py`,
  `datalad_helper_scripts/batch_remove_deprecated_URLs.py`, and
  `datalad_crawlers/` manage archives, access URLs, or remote files.
- **DATS:** `dats_validator/` validates metadata;
  `dats_jsonld_annotator/` adds JSON-LD annotations;
  `DATS2csv/` exports selected fields; and `conp_to_nidm_terms/` reports terms
  or generates JSON-LD.
- **Reports:** `data_aggregation_summary_scripts/` creates CSV summaries of
  datasets and tools.
- **Repository checks:** `check_dataset_filenames.py` checks tracked paths for
  filename compatibility across platforms.

For file-by-file maintenance recommendations, see
[REPORT-SCRIPTS.md](REPORT-SCRIPTS.md). For contributor guidance, see
[DEVELOPMENT.md](DEVELOPMENT.md).

## Before running a command

1. Read the script's module description and command-line help/source.
2. Confirm whether it downloads data, changes Git/DataLad state, writes output,
   or contacts a remote service.
3. Use a disposable clone or test dataset when validating a mutating workflow.
4. Keep API keys and access tokens out of tracked files, logs, and shared output.

Use the repository's documented Python environment and dependencies. Several
utilities also require DataLad, Git-annex, Perl modules, or access to external
services. Their behavior can depend on locally available datasets and
credentials.
