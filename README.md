# CONP dataset

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

## Requirements

* [Git](https://git-scm.com/downloads)
* [Git annex](http://git-annex.branchable.com/install)
* DataLad: `pip install git+https://github.com/datalad/datalad.git`

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

## Contributing

This repository has multiple git submodules pointing at dataset instances available in the [conpdatasets](https://github.com/conpdatasets) repository.
Therefore, to contribute to such datasets it is required that collaborators have push access to both repositories.

In addition, it is important to keep in mind that the conpdatasets repository is a fork of the [OpenNeuroDatasets](https://github.com/OpenNeuroDatasets/ds001634) project. 
Thus, when raising a PR, contributors should be careful to request branch merge to `conpdatasets:master` rather than to `OpenNeuroDatasers:master`, which comes as default option but is not currently approved.