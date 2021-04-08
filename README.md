# CONP dataset

[![CircleCI](https://circleci.com/gh/CONP-PCNO/conp-dataset.svg?style=shield)](https://circleci.com/gh/CONP-PCNO/conp-dataset)

CONP dataset is a repository containing the datasets available in the
Canadian Open Neuroscience Platform. It leverages
[DataLad](http://datalad.org) to store metadata and references to
data files distributed in various storage spaces and accessible depending on each data owner's
policy.

The instructions below explain how to find and get data from the dataset.
You can also add data by following the instructions in our [contribution
guidelines](https://github.com/CONP-PCNO/conp-dataset/blob/master/.github/CONTRIBUTING.md).
We welcome your feedback! :smiley:

## Dataset structure

The dataset is structured as follows:

- `investigators` contains sub-datasets for investigators.
- `projects` contains sub-datasets for projects.

Investigators and projects are responsible for the management and curation
of their own sub-datasets.

## Installing required software

### git

`sudo apt-get install git`

It is useful to configure your `git` credentials to avoid having to enter them repeatedly:

`git config --global user.name "yourusername"`
`git config --global user.email "your.name@your.institution.ca"`

### git-annex

First install the neurodebian package repository:

`sudo apt-get install neurodebian`

Then install the version of git-annex included in this repository:

`sudo apt-get install git-annex-standalone`

The version of git-annex installed can be verified with:

`git annex version`

As of May 12 2020, this installs git annex v 8.20200330, which works with CONP datasets. Earlier versions of git-annex may not.

### DataLad:

`sudo apt-get install datalad`

## Getting the data

Install the main CONP dataset on your computer:

```console
datalad install -r http://github.com/CONP-PCNO/conp-dataset
```

Get the files you are interested in:

```console
datalad get <file_name>
```

This may require authentication depending on the data owner's configuration.

You can also search for relevant files and sub-datasets:

```console
datalad search T1
```

## Tests

1. Execute `python tests/create_tests.py` from the root of conp-dataset repository
2. Run `pytest tests/` to execute tests for all datasets in projects and investigators
3. To run specific test on specific datasets, run `pytest tests/test_<name of dataset>` like
   `pytest tests/test_projects_SIMON-dataset`

For detailed explanations of the tests, please consult the [test suite documentation](https://github.com/CONP-PCNO/conp-dataset/blob/master/tests/README.md).

## Coding standards

To keep the Python code maintainable and readable a suite of QA pipelines is testing the code assuring code standards.
Pull requests will trigger a GitHub workflow executing pre-commit.

To execute pre-commit locally, you will need to [install pre-commit](https://pre-commit.com/#installation) using your favorite method.
Then, run:
```bash
pre-commit install

pre-commit run --all-files
```
Pre-commit won't let you commit until reported issue are fixed.
If problematic, you can optionally skip the pre-commit for a local commit using the `--no-verify` flag when commiting, however this will still perform QA test on your PR.
