# Contribution			

New contributions are more than welcome! ❤️

## Contribution workflow

You should perform the workflow below if:
 1. you are planning to add a new dataset
 2. you are adding data to an already existing dataset
 3. you are making any changes (e.g. fixing a typo or a bug)

Please perform the following steps:
1. Fork this repository, or make sure that your existing fork is up-to-date.
2. Clone your fork on your local computer, or make sure that your existing clone
is up-to-date.
3. Edit your local clone, and commit your changes using `datalad save`.
4. Push your changes to your fork using `datalad publish`.
5. Open a pull request (PR) to the main repository.
For steps 3. and 4., see detailed instructions in the sections below.

If you are not familiar with
these steps, we suggest to read [GitHub documentation](https://help.github.com/en),
in particular the articles on [forks]
(https://help.github.com/en/articles/working-with-forks) and [pull
requests](https://help.github.com/en/articles/creating-a-pull-request-from-a-fork).

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

4. Publish the modifications to your fork of the main dataset:

    From the main repository (`conp-dataset`):
    ```console
    datalad save
    datalad publish --to origin
    ```

## Adding meta-data

Adding meta-data about your dataset is required. Metadata has to be added in
a JSON file with the following attributes based on [bioCADDIE
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

## Re-using existing data

You can reuse any published dataset in your own dataset. For instance,
to add data from the [CoRR](http://fcon_1000.projects.nitrc.org/indi/CoRR/html):
```
datalad install -d . --source ///corr/RawDataBIDS CorrBIDS
```
Datasets available in DataLad are listed [here](http://datasets.datalad.org).
