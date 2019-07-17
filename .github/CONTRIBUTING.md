# Contribution			

New contributions are more than welcome! ❤️

Before you start, we suggest that you get familiar with git and GitHub
 as our contribution workflow heavily relies on these tools. If
you have never used git, a good quick start guide is available
[here](https://rogerdudler.github.io/git-guide). If you're looking for more
comprehensive training, you can check [this](https://try.github.io) out.
GitHub guides are available [here](https://guides.github.com). We will also
refer to specific sections of them in the instructions below.

One last thing before we start: if you need help at any stage, please [open
an issue](https://github.com/CONP-PCNO/conp-dataset/issues/new/choose) in
this repository. We'll do our best to help you!

## Contribution workflow

You should perform the workflow below if:
 1. you are planning to add a new dataset
 2. you are adding data to an already existing dataset
 3. you are making any changes (e.g. fixing a typo or a bug)

Please perform the following steps:
1. [Fork](https://help.github.com/en/articles/working-with-forks) this repository, or make sure that your existing fork is up-to-date.
2. Clone your fork on your local computer, or make sure that your existing clone
is up-to-date.
3. Edit your local clone, and commit your changes using `datalad save`.
4. Push your changes to your fork using `datalad publish`.
5. Get a DOI for your dataset.
6. Open a [pull
request](https://help.github.com/en/articles/creating-a-pull-request-from-a-fork) (PR) to the main repository.
For steps 3., 4. and 5., see detailed instructions in Section "Adding data" below.

Your PR will be reviewed by at least two members of our technical team. They will
make sure that your contribution meets the quality standards for inclusion
in this repository. Refer to the [PR
template](https://github.com/CONP-PCNO/conp-dataset/.github/PULL_REQUEST_TEMPLATE.md)
for more information about PR evaluations.

## Adding data

You can create a sub-dataset in the CONP repository as follows:

1. Create your sub-dataset in your cloned fork, under `investigators` or `projects`. For instance:

```console
datalad create -d . investigators/<username>
```

2. Publish your sub-dataset:

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

3. Add files to your sub-dataset:

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

4. Add metadata to your dataset

Adding meta-data about your dataset is required. Metadata has to be added
in a JSON file called `dats.json`, located at the root of your dataset, and
containing the following attributes based on [bioCADDIE
DATS](https://github.com/biocaddie/WG3-MetadataSpecifications):
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

Examples are available at [metadata/example](https://github.com/CONP-PCNO/conp-dataset/tree/master/metadata/example).

5. Publish the modifications to your fork of the main dataset:

    From the main repository (`conp-dataset`):
    ```console
    datalad save
    datalad publish --to origin
    ```

6. Get a Digital Object Identifier for your dataset

Datasets in CONP are required to have a Digital Object Identifier (DOI). A
DOI is a unique and permanent identifier associated with a research object
to make it citeable and retrievable. To get a DOI for your dataset, follow
the following steps:

a. Log in to [Zenodo](https://zenodo.org), preferably using your GitHub
account.
b. [Flip the switch](https://zenodo.org/account/settings/github) of your
dataset GitHub repository.
c. Release your dataset on GitHub (see instructions
[here](https://help.github.com/en/articles/creating-releases)).
d. This will create a DOI and archive your dataset on Zenodo. Get the DOI
badge from [here](https://zenodo.org/account/settings/github/) and add it
to the `README.md` file of your dataset.
e. The DOI badge links to the DOI associated with the latest DOI of your dataset. 
   Add this link to your DATS model.

## Re-using existing data

You can reuse any published dataset in your own dataset. For instance,
to add data from the [CoRR](http://fcon_1000.projects.nitrc.org/indi/CoRR/html):
```
datalad install -d . --source ///corr/RawDataBIDS CorrBIDS
```
Datasets available in DataLad are listed [here](http://datasets.datalad.org).
