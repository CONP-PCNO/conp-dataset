# CONP dataset

[![CircleCI](https://circleci.com/gh/CONP-PCNO/conp-dataset.svg?style=shield)](https://circleci.com/gh/CONP-PCNO/conp-dataset)

**"CONP dataset"** is a repository containing the datasets available through the [CONP Portal](https://portal.conp.ca/). It uses [DataLad](http://datalad.org) to store metadata and references to data files distributed in various storage spaces and accessible according to each data owner's policy.

The instructions below explain how to install the necessary software and fetch data from a given dataset. You can also add dataset to the CONP Portal by following the instructions in our [contribution guidelines](https://github.com/CONP-PCNO/conp-dataset/blob/master/.github/CONTRIBUTING.md). We welcome your feedback! :smiley:

## Dataset structure

Datasets are contained in each directory listed under projects `projects`. Each project maintainer is responsible for the management and curation of their own datasets.

## Installing required software - Method 1: NeuroDebian

The following instructions assume a relatively recent Ubuntu- or Debian-based Linux system, though equivalent steps can be taken with other operating systems.

One of the most convenient ways of installing a host of neuro-related software is through the [Neurodebian](https://neuro.debian.net/) repository.  For the following installation procedure, we will assume the use of NeuroDebian, which is installed with:

```
sudo apt-get update
sudo apt-get install neurodebian
```

### Python

The CONP recommends you use Python version 3.12 and up. You can check your Python version with:

```python --version```or ```python3 --version```

### git

```sudo apt-get install git```

It is strongly recommended that you configure your `git` credentials to avoid having to enter them repeatedly or other complications when using DataLad:

```git config --global user.name "Jane Doe"```

Replace “John Doe” with your name.

```git config --global user.email “janedoe@example.com”```

Replace “janedoe@example.com” with your email address.

### git-annex

```
sudo apt-get install git-annex-standalone
```

As of May 12 2020, this installs git annex version 8.20200330, which works with CONP datasets. Earlier versions of git-annex may not. The version of git-annex installed can be verified with:

```git annex version```

### DataLad

```sudo apt-get install datalad```

## Installing required software - Method 2: `pip`

The same requirements for `Python` and `git` apply from the previous section.

Recent versions of Ubuntu-based distributions (e.g., based on 24.04 LTS) require virtual environments for external Python packages.  You can use `venv` or `pipx` to do this. The easiest for most users is probably to use `pipx`, in which case `git-annex` and `datalad` are installed with the following commands:

```
pipx install datalad-installer
datalad-installer git-annex -m datalad/git-annex:release
git config --global filter.annex.process "git-annex filter-process"
pipx install datalad
```

## Downloading data

Install the main CONP dataset on your computer:

```
datalad install -r http://github.com/CONP-PCNO/conp-dataset
```

Install the specific dataset you are interested in:

```
cd conp-dataset/projects
datalad install <project name>
```

Get the files you are interested in:

```
cd <project name>
datalad get <file_name>
```

This may require authentication depending on the data owner's configuration.  The CONP Portal dataset page corresponding to the dataset you are interested in will indicate whether an account and credentials are required to access data.

You can also search for relevant files and sub-datasets, for example:

```
datalad search T1
```

## Tests

For detailed explanations of the tests, please consult the [test suite documentation](https://github.com/CONP-PCNO/conp-dataset/blob/master/tests/README.md).

1. Execute `python tests/create_tests.py` from the root of conp-dataset repository.
2. Run `pytest tests/` to execute tests for all datasets in projects and investigators.
3. To run a specific test on a specific dataset, run `pytest tests/test_<name of dataset>`, e.g., `pytest tests/test_projects_SIMON-dataset`


## Coding standards

To keep the Python code maintainable and readable, a suite of quality-assurance pipelines tests the code. Pull requests will trigger a GitHub workflow executing pre-commit.

To execute pre-commit locally, you will need to [install pre-commit](https://pre-commit.com/#installation) using your favorite method. Then, run:

```bash
pre-commit install
pre-commit run --all-files
```

Pre-commit won't let you commit until reported issues are fixed. If problematic, you can optionally skip the pre-commit for a local commit using the `--no-verify` flag when committing, however this will still perform QA test on your PR.
