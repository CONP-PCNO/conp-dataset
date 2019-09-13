# CONP dataset

[![Build Status](https://travis-ci.org/CONP-PCNO/conp-dataset.svg?branch=master)](https://travis-ci.org/CONP-PCNO/conp-dataset)

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

* `investigators` contains sub-datasets for investigators.
* `projects` contains sub-datasets for projects.

Investigators and projects are responsible for the management and curation 
of their own sub-datasets.

## Installing required software 

### git

```sudo apt-get install git```

It is useful to configure your ```git``` credentials to avoid having to enter them repeatedly: 

```git config --global user.name "yourusername"```
```git config --global user.email "your.name@your.institution.ca"```

### git-annex

First install the neurodebian package repository:

```sudo apt-get install neurodebian```

Then install the version of git-annex included in this repository:

```sudo apt-get install git-annex-standalone```

The version of git-annex installed can be verified with:

```git annex version```

As of August 14 2019, this installs git annex v 7.20190730, which works with CONP datasets.  Earlier versions of git-annex may not.

### DataLad: 

```sudo apt-get install datalad```

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

You can also search for relevant files and sub-datasets as follows:

```console
datalad search T1
```


## Tests

1. Execute `python tests/create_tests.py` from the root of conp-dataset repository
2. Run `pytest tests/` to execute tests for all datasets in projects and investigators
3. To run specific test on specific datasets, run `pytest tests/test_<name of dataset>` like
`pytest tests/test_SIMON-dataset`
