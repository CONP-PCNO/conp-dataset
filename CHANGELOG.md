# Changelog

## Unreleased

### Added

- Added scripts to import individual Zenodo records and OSF nodes into local
  DataLad datasets. The importers download text files directly, register other
  files with Git-annex, generate or update `README.md` and `DATS.json`, and save
  the resulting dataset. The OSF importer also traverses project components
  and supports token-based access.
- Added `scripts/how_to_use_import_single_scripts.md` with example commands for
  both importers.
