# CONP dataset

CONP dataset is a repository containing the datasets available in the 
Canadian Open Neuroscience Platform. It leverages 
[DataLad](http://datalad.org) to store metadata and references to 
data files distributed in various storage spaces and accessible depending on each data owner's 
policy.

## Dataset structure

The dataset is structured as follows:

* `investigators` contains sub-datasets for investigators based in Canada.
* `projects` contains sub-datasets for projects hosted in Canada.

Investigators and projects are responsible for the management and curation 
of their own sub-datasets.

## Accessing data

Requirements:

* [Git](https://git-scm.com/downloads)
* [Git annex](http://git-annex.branchable.com/install)
* DataLad: `pip install git+https://github.com/datalad/datalad.git`

To start, clone the CONP dataset on your computer:

```git clone http://github.com/CONP-PCNO/conp-data```

You can then search for relevant files and sub-datasets as follows:

```datalad search T1```

And you can finally get the files you are interested in by typing:

```datalad get <file_name>```

This may require authentication depending on the data owner's configuration.

## Adding data

If you are an investigator or a project manager, you can create a 
sub-dataset in the CONP repository as follows:

1. Fork the CONP data repository on GitHub. This will create a copy of the dataset at `http://github.com:<github_username>/conp-dataset`.
2. Clone your fork on your computer:

```git clone git@github.com:<github_username>/conp-dataset```

3. Create your sub-dataset in your cloned fork, under `investigators` or `projects`. For instance:

```
datalad create -d . investigators/<your_name>
```

4. Publish your sub-dataset:

    From the main repository (`conp-dataset`):

    a. Add a sibling for your dataset on GitHub:

    ```datalad create-sibling-github conp-dataset-<name>```

    DataLad will ask your GitHub user name and password to create the sibling.

    b. Update the `.gitmodules` file to add your sibling. It should contain a section that looks like this:

    ```
    [submodule "investigators/<username>"]
        path = investigators/<username>
        url = git@github.com:<username>/conp-dataset-<username>.git
    ```

    Note the Git endpoint in the url.

    c. Commit the modified `.gitmodules` file:

    ```console
    git add .gitmodules
    git commit -m "Updated .gitmodules"
    ```

5. Add files to your sub-dataset

    From your sub-dataset (`investigators/<username>`):
    
    a. Create and add a README.md file, directly in the Git repository:
    `datalad add --to-git ./README.md`
    
    b. Add a file accessible through http (for instance an image file):
    `git annex addurl <url>`
    
    c. Publish the modifications:
    `datalad save`
    `datalad publish --to github`
    
7. Publish the modifications to the main dataset:
    From the main repository (`conp-dataset`):
    `datalad save`
    `datalad publish --to origin`

8. Create a pull request.

Once the pull request is accepted by the CONP data managers, your 
dataset is created. It is then up to you to manage its content and 
decide on the creation of sub-datasets in it. You may want to host your 
sub-dataset on GitHub to facilitate its management. Modifications to 
your dataset can be propagated to the CONP dataset through pull 
requests, by repeating steps 4 and 5 above.

We welcome your feedback! :smiley:
