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

### Python tooling and dependencies

- Pin the repository Python version to 3.12.3.
- Replace the scattered `requirements.txt` files with a non-packaged uv project in
  `pyproject.toml` and a committed `uv.lock`. Declare runtime and development
  dependencies centrally, and update the Docker image and contributor instructions
  to use uv.
- During the transition to uv, update the legacy requirements to current DataLad
  and DataLad OSF release lines and add git-annex 10. Those requirements files were
  subsequently removed in favor of the uv project and lockfile.
- Enable `jsonschema`'s `format` extra so DATS validation checks URI, IRI, and
  other supported JSON Schema formats rather than silently accepting unvalidated
  format values.
- Modernize pre-commit hooks: consolidate Python linting, import sorting, and
  formatting under Ruff; update the core hook revisions; and add private-key
  detection and a 500 KB added-file limit. Retain the repository-specific
  Dockerfile and documentation checks.
- Replace the Dockerfilelint pre-commit hook with Hadolint.
- Centralize the Ruff target Python version, line length, selected rules,
  exclusions, and development dependency in `pyproject.toml`
- Fixed the Ruff findings across the Python scripts/ and tests/.
- Organize `.gitignore` into sections and cover local environments, Python and
  test caches, generated dataset tests, local environment files, build and
  coverage output, logs, and common operating-system files.

### Continuous integration

- Add pull-request validation for dataset filenames across the CONP superdataset
  and its pinned DataLad subdatasets. Detect case-insensitive and Unicode
  normalization collisions and Windows-incompatible/reserved names; report
  existing findings while blocking only newly introduced issues.
- Add a local pre-commit check and document how to run it. The checker inspects
  Git-tracked paths only, does not download git-annex content, and reports
  incomplete local scans when subdatasets are unavailable.
- Remove CircleCI configuration, its Docker image, and its CircleCI artifact
  reporting script and documentation.
- Move pull-request dataset test selection from CircleCI-specific environment
  variables to GitHub Actions event data. Retrieve all changed files through the
  paginated GitHub pull request API and retain the minimal-dataset selection
  behavior.
- Skip tests requiring private dataset credentials on GitHub Actions pull request
  runs, and replace CircleCI-specific credential guidance with general test
  environment instructions.
- Update GitHub Actions workflows to use Ubuntu 24.04. Avoid checking out
  submodules in the pre-commit workflow, set up uv there, and include the Python,
  Docker, and uv lock files in Docker image rebuild path filters.
- Update the submodule maintenance workflow runner and refresh the Docker build
  action configuration.
- Configure Dependabot to group GitHub Actions updates, limit concurrent update
  pull requests, standardize commit-message prefixes, and exclude dataset
  submodule paths.

### Testing

- Make DATS validator fixture tests independent of GitHub availability by
  mocking the `derivedFrom` existence check instead of issuing a live request.

### Repository maintenance

- Update the Docker image build configuration to use current Ubuntu and Docker
  tooling.
- Update the license copyright year to 2026.
- Adjust the automatic pull-request reviewer list.
