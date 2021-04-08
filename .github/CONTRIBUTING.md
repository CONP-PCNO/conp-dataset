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
1. [Fork](https://help.github.com/en/articles/working-with-forks) this repository, or ensure that your existing fork is up-to-date.
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

You can create a sub-dataset in the CONP repository in two ways:

1. Using Zenodo
    1. Upload your dataset to https://zenodo.org with the specific keyword `canadian-open-neuroscience-platform` if the dataset is less than 50GB and if it is more than 50GB, please contact [Zenodo](https://zenodo.org/support) with a request category of `File upload quota increase` in order to be able to upload it
    2. If you set the dataset as restricted, create a personal token via Applications > Personal access tokens > New Token > Check all scopes > Create. Then send the token via email to CONP Technical Steering Committee member Tristan Glatard (tglatard@encs.concordia.ca).
2. Upload manually the data using datalad and the command line (see instructions below)

Note: Please don't forget to add a `README.md` at the root directory of your dataset.
Adding meta-data about your dataset is required. Metadata has to be added
in a JSON file called `DATS.json`, located at the root of your dataset, and
containing the following attributes based on [bioCADDIE
DATS](https://github.com/datatagsuite/schema):
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

### Uploading the dataset manually

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

Please refer to the Adding data notes

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


### Updating the dataset manually

#### Dataset as git submodules

Any existing dataset can be added to CONP-PCNO repository as a git submodule. By doing that, the original dataset repository will be added as a subdirectory of CONP-PCNO which will manage it independently.
Therefore, by definition of submodules, CONP-PCNO will only hold a reference to the actual dataset which will continue to live in its original space. Additional information on how submodules work can be found [here](https://git-scm.com/book/it/v2/Git-Tools-Submodules).
The current list of submodules in CONP-PCNO can be found under the [CONP-datasets/project](https://github.com/CONP-PCNO/conp-dataset/tree/master/projects) folder.


#### Updating a dataset on origin

Often a dataset will need to be updated with recent additions. Here we describe the full dataset and git submodule update
procedural steps with a schematic summary shown below:

1 - Given the nature of a submodule reference, users accessing a dataset in CONP-PCNO will be redirected
to the original dataset location, or origin. Therefore the origin is the first place where a dataset update process starts.
In the schematic below the reference between a dataset in CONP-dataset and the dataset origin is represented with a long arrow. The
original dataset repository is shown as [conpdataset repository](https://github.com/conpdatasets) as an example.
The first step consists in cloning the original dataset repository to develop changes.

2 - Dataset changes must be approved and merged to master so that the corresponding git submodule in CONP-PCNO
will be able to update its reference and point to the latest commit at the origin

3 - The third step involves updating the git submodule on the CONP-PCNO repository side to finally reflect recent changes in the dataset.
A list of commands to accomplish this step is given in the next section on Updating a Git submodule

The following schematic helps to visualize the three points just described:

![](/docs/conpdataset-CONP%20interaction%20submodules%20update.png)


#### Updating a Git submodule to the latest commit on origin

1 - Clone the forked repository and go to projects
```
git clone git@github.com:<your_username>/conp-dataset.git
cd conp-dataset/projects
```
2 - Make a new branch to work on
```
git checkout -b <new_branch>
```
3 - If it is the *first time* the submodule gets updated then use ```--init``` first, otherwise skip to 4
```
git submodule update --init --recursive <submodule_name>
```
4 - Run the following command
```
git submodule update --recursive --remote <submodule_name>
```
The option ```--remote``` supports updating to latest tips of remote branches

5 - Commit and push your changes

## Re-using existing data

You can reuse any published dataset in your own dataset. For instance,
to add data from the [CoRR](http://fcon_1000.projects.nitrc.org/indi/CoRR/html):
```
datalad install -d . --source ///corr/RawDataBIDS CorrBIDS
```
Datasets available in DataLad are listed [here](http://datasets.datalad.org).
