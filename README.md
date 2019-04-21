# CONP dataset

CONP dataset is a repository containing the datasets available in the 
Canadian Open Neuroscience Platform. It leverages 
[DataLad](http://datalad.org) to store metadata and references to 
data files distributed in various storage spaces and accessible depending on each data owner's 
policy.

We welcome your feedback! :smiley:

## Dataset structure

The dataset is structured as follows:

* `investigators` contains sub-datasets for investigators based in Canada.
* `projects` contains sub-datasets for projects hosted in Canada.

Investigators and projects are responsible for the management and curation 
of their own sub-datasets.

## Requirements

* [Git](https://git-scm.com/downloads)
* [Git annex](http://git-annex.branchable.com/install)
* DataLad: `pip install git+https://github.com/datalad/datalad.git`

## Accessing data

To start, install the main CONP dataset on your computer:

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


## Adding data

If you are an investigator or a project manager, you can create a 
sub-dataset in the CONP repository as follows:

1. Fork the CONP data repository on GitHub:
   * Navigate to http://github.com/CONP-PCNO/conp-dataset (this page)
   * In the top-right corner of the page, click Fork. 
   * This will create a copy of the dataset at http://github.com:username/conp-dataset

2. Install your fork on your computer:

```console
datalad install git@github.com:<username>/conp-dataset
```

3. Create your sub-dataset in your cloned fork, under `investigators` or `projects`. For instance:

```console
datalad create -d . investigators/<username>
```

4. Publish your sub-dataset:

    From the main repository (`conp-dataset`):

    a. Add a sibling for your dataset on GitHub:

    ```console
    datalad create-sibling-github -d investigators/<username> conp-dataset-<username>
    ```

    DataLad will ask your GitHub user name and password to create the sibling.

    b. Update the `.gitmodules` file to add your sibling. It should contain a section that looks like this:

    ```
    [submodule "investigators/<username>"]
        path = investigators/<username>
        url = http://github.com:<username>/conp-dataset-<username>.git
    ```

    Note the Git endpoint in the url.

5. Add files to your sub-dataset:

    From your sub-dataset (`investigators/<username>`):
    
    a. Create and add a README.md file, directly in the Git repository:
    ```console
    datalad add --to-git ./README.md
    ```

    b. Add data files:
    * Files that are already accessible through http:
    ```console
    git annex addurl <url> --file <local_path>
    ```

    * Files that you want to make available through Google Drive:
    ```console
    pip install git+https://github.com/glatard/git-annex-remote-googledrive.git@dev
    git-annex-remote-googledrive setup
    git annex initremote google type=external externaltype=googledrive prefix=CONP-data root_id=<folder_id> chunk=50MiB encryption=shared mac=HMACSHA512
    ```
    where `<folder_id>` is the id of the Google Drive folder where you want to upload the files. Don't forget to 
    check the permissions of this folder, for instance, make it world-readable if you want your files to be
    world readable. Assuming that you want to add image.nii.gz to the dataset:
    ```console
    datalad add image.nii.gz
    git annex copy image.nii.gz --to google
    ```

    c. Publish the modifications:
    ```console
    datalad save
    datalad publish --to github
    ```
    
7. Publish the modifications to your fork of the main dataset:

    From the main repository (`conp-dataset`):
    ```console
    datalad save
    datalad publish --to origin
    ```

8. Publish modifications to the main dataset:

    Create a new pull request from http://github.com:username/conp-dataset to http://github.com/CONP-PCNO/conp-dataset.

    TODO: add a screenshot here.

Once the pull request is accepted by the CONP data managers, your 
dataset is created in the CONP repository. It is then up to you to manage its content and 
decide on the creation of sub-datasets in it. Modifications to 
your dataset can be propagated to the CONP dataset through pull 
requests, by repeating the last step above.

## dataset meta-data

Adding meta-data about your dataset is recommended. Although there is no standard yet for CONP, preliminary work favor a JSON file with the following attributes based on [bioCADDIE DATS](https://github.com/biocaddie/WG3-MetadataSpecifications):
- schema
- title
- description
- dates
- creators
- storedIn
- type
- version
- privacy
- licenses

example are available at [metadata/example](metadata/example).

## Re-using existing data

You can easily reuse any published dataset in your own dataset. For instance,
to add data from the [CoRR](http://fcon_1000.projects.nitrc.org/indi/CoRR/html):
```
datalad install -d . --source ///corr/RawDataBIDS CorrBIDS
```
Datasets available in DataLad are listed [here](http://datasets.datalad.org).


# Pull Request workflow

To test a PR that proposes the addition of a new dataset, this is a possible workflow:

1. To create the PR, you should work on your fork of of conp-dataset (eg github://jbpoline/conp-dataset)
2. Make sure your fork master branch is not ahead of github://conp-pcno/conp-dataset master branch
2. Clone your fork locally, eg 
```
mkdir myfork-of-conp-dataset
cd myfork-of-conp-dataset
git clone git@github.com:jbpoline/conp-dataset.git
```
3. Add the remote from which the PR comes from (unless it comes from a branch of conp-dataset), for instance if the PR comes from the `myfriend-fork` github handle (and check that the remote is added):
```
git remote add myfriend-fork git@github.com:myfriend-fork/conp-dataset.git
git remote -vv 
``` 
4. Pull the pull request to your local fork, for instance if it is in master of `myfriend-fork`: 
```
git pull myfriend-fork master
```
5. Push to your local fork in master
git push origin master:master

6. Datalad install this 
```
datalad install -r https://github.com/jbpoline/conp-dataset.git
```
7. Check there that all is fine:
- the `git annex whereis` is giving sensible urls
- the `datalad get` work for open data
- ...





