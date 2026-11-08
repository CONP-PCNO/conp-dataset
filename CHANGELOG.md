# Changelog

## Unreleased

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
- Organize `.gitignore` into sections and cover local environments, Python and
  test caches, generated dataset tests, local environment files, build and
  coverage output, logs, and common operating-system files.

### Continuous integration

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

### Repository maintenance

- Update the Docker image build configuration to use current Ubuntu and Docker
  tooling.
- Update the license copyright year to 2026.
- Adjust the automatic pull-request reviewer list.
