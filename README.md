# CONP dataset

CONP dataset is a repository containing the datasets available in the 
Canadian Open Neuroscience Platform. It leverages 
[DataLad](http://datalad.org) to store metadata and references to 
data files distributed in various storage spaces and accessible depending on each data owner's 
policy.

The instructions below explain how to find and get data from the dataset.
You can also add data by following the instructions in our [contribution
guidelines](https://github.com/CONP-PCNO/conp-dataset/.github/CONTRIBUTING.md).
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

```
datalad install -r https://github.com/<mygithubhandle>/conp-dataset.git
```

8. Check there that all is fine:
- the `git annex whereis` is giving sensible urls
- the `datalad get` work for open data
- ...


## To download data from Google Drive:

### Initial setup:

1. If you do not have pip3 installed:

```
    sudo apt install python3-pip
```

2. Install the git annex remote for Google Drive:

```
    pip3 install git-annex-remote-googledrive
```

Steps 1 and 2 only need to be done once.

### Downloading datasets:


3. download the CONP dataset from your fork of the repository:

```
    datalad install -r http://github.com/<your_user_name>/conp-dataset
```

4. For each project you are interested in: (e.g. conp-dataset/projects/<your_project>) set up the Google Drive remote in that project's directory:
 
```
    git annex init
    git-annex-remote-googledrive setup
```

  The `git-annex-remote-googledrive setup` command provides a link to authorise the Google Drive remote.

a.  Open this link and connect it to a Google account, which will give you an authorisation code.

b.  Copy and paste the code into your terminal window to complete setting up the Google Drive remote.

c.  Connect the project to the Google Drive remote: 

```
    datalad siblings -d "</full/path/to/your_project>" enable -s google
```

d. Retrieve the files of interest as with other backends

```
    datalad get <your_file_name>
```

### Example:

```
  datalad install -r http://github.com/emmetaobrien/conp-dataset
  cd conp-dataset/projects/1KGP-GoogleDrive-27Jun2019
  git annex init
  git-annex-remote-googledrive setup
  datalad siblings -d "/home/emmetaobrien/conp-dataset/projects/1KGP-GoogleDrive-27Jun2019" enable -s google
  datalad get *
```


### Notes:

* Only the version of git-annex-remote-googledrive installed with pip3 is observed to work for this process; using older versions of pip can cause problems.

* If the Google Drive remote is not correctly set up, the project directory will appear to contain correctly formed git-annex links, but they will not connect to anything.

