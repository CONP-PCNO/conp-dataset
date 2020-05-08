# CONP dataset - Test suite

[![CircleCI](https://circleci.com/gh/CONP-PCNO/conp-dataset.svg?style=shield)](https://circleci.com/gh/CONP-PCNO/conp-dataset)

# Dependencies

## git-annex

We recommend using git-annex version 8.20200330 and above.
You can get git-annex by usign our CircleCI container, getting the latest
binaries, or using your package manager ([see here](https://git-annex.branchable.com/install/)). We favor using our CircleCI container to improve reproducibility of
the test suite.

#### CircleCI container

The latest version of the container used for testing can be obtained from Docker
Hub:

```bash
docker pull mathdugre/conp-dataset:latest
```

#### Latest binaries

The latest version _git-annex_ binaires can be obtained using the following command:

```bash
curl https://downloads.kitenet.net/git-annex/linux/current/git-annex-standalone-amd64.tar.gz | tar -zxvf -
```

You will then need to add the folder to your path.

```bash
# .bashrc

export PATH="/path/to/git-annex/folder":$PATH
```

## Python modules

To run the test suite you will need to install the project module requirements
for Pyhton. Since there are multiple location for the _requirements.txt_ files
we recommend to use the below command at the root of the repository to install
all of the Python dependencies.

```bash
find . -name requirements.txt | xargs -I{} pip install -r {}
```

# Executing the test suite

Once all dependencies are installed, you will be ready to run the test suite.
You can run them using this command at the root of the repository:

```bash
python -m venv venv
. venv/bin/activate
PYTHONPATH=$PWD pytest tests/test_*
```

### Optinal flags

- -v : Verbose mode.
- -s : Display print statement from in the output.
- -rfEs : Show extra summary for (f)ailed, (E)rror, and (s)kipped.
- -n=N : Run N tests in parallel.

# Test Suite Structure

## Relevant code base components

```
.
├── scripts
│ ├── Crawlers
│ ├── dats_validator
│ │ └── requirements.txt
│ └── unlock.py             # Inject zenodo token into annex urls.
├── tests
│ ├── create_tests.py       # Generate a test file for each dataset, when required.
│ ├── functions.py          # Contains all the utility functions for testing.
│ ├── parse_results.py      # Parse the test results into a json file.
│ ├── requirements.txt
│ └── template.py           # Regroup the test methods for dataset.
└── requirements.txt
```

<!-- Utility functions -->
<!-- Template -->
<!-- Test generation -->

## Workflow in CircleCI

```
                                       worker x2
                                ┌──────────────────────┐
                                │         Test         │
                                ╞══════════════════════╡
  worker x1       split test    │      has_readme      │   Parse test results
┌───────────┐  suite by timing  ├──────────────────────┤      & save them
│   Build   ├────────>>>────────┤    has_valid_dats    ├──────────>>>────────── END
└───────────┘                   ├──────────────────────┤
                                │     datalas_get      │
                                ├──────────────────────┤
                                │   files_integrity    │
                                └──────────────────────┘
```

The workflow is composed of two job: build and test.

**Build job:**

- No parallelism
- Install the dependencies and save them to the workspace for subsequent jobs.

Before test job:<br/>
The test suite is split by historical timing to run on multiple worker. This aims at reducing the total execution time.

**Test job:**

- Parallelism on 2 workers
- Execute the dataset template test suite

After test job: (WIP)<br/>
The test results are parsed and save to CircleCI artifacts.
#TODO Send them to a monitoring GitHub Repository

# Life of a dataset test

This section describe the different steps a dataset test will perform to validate the proper functioning of datasets.

## Test creation

At the start of the test job, the `template.py` file is used to generate a test file for each dataset.
Changes made to a dataset should not influence the behavior of other datasets while changes to the test suite potentially impacts every datasets.
To solve this, the test suite will start by retrieving all files modified during a pull request.
Then, it will only test on the minimal set of datasets.
This strategy aims at saving computing resources as well as time.

To select wether a dataset should be tested or not, we follow this heuristic:

1. File modified is **not** part of a dataset:
   - is part of a whitelist (see below), then **ignore**.
   - otherwise, **full rerun** of the test suite.
2. File is part of a dataset, then **partial rerun** test for this dataset.

```
Whitelist
┌─────────────┬────────────────────┐
│ Exact match │ Contains pattern   │
├─────────────┼────────────────────┤
│  .datalad   │  .git              │
│  docs       │  README            │
│  metadata   │  LICENSE           │
│             │  requirements.txt  │
└─────────────┴────────────────────┘
```

## Dataset validation

During this phase of the test suite, the a dataset will be subjected to the different tests below to ensure that their content is valid with the CONP portal convention.
Once a dataset passes the whole test suite, we can be more confident that it will be functional for other users.

### Datalad Install **(Setup)**

This steps runs before every test case mentioned below.
To prevent concurent execution of the command to cause issue, test case for a dataset are queued when the dataset is already being installed.

### Has `README.md`

Every dataset is required to have a `README.md` file to describe its content.
This test validates that this file exist.

### Has a valid `DATS.json` file

Every dataset must have a `DATS.json` that follows that [DATS model convention](https://datatagsuite.github.io/docs/html/dats.html).
This test makes sure that the `DATS.json` file exist and that its content is conform to the DATS Model.

### Datalad Get

The ability to download a dataset is a critical component for its proper function.
This test goes through the process of downloading files from a dataset to valid its validity.
That is, the test case executes those steps:

1. Authenicate the dataset (see [Authenticated Dataset](#authenticated-dataset) section).
1. (**Travis specific**) Remove files using FTP due to issue on travis; more detail [here](https://blog.travis-ci.com/2018-07-23-the-tale-of-ftp-at-travis-ci).
1. Select a k files, with samllest size, from a sample of n files. This aims at saving computing resources (see [Timeout](#timeout) and [Size of Annexed File](#size-of-annexed-file) sections).
1. Use `datalad get` to download each of the k files formt the sample.

### Files Integrity

Downloading every files in a dataset to assure the proper functioning of a dataset would be rather unpractical, however, verifying the integrity of files is more rational approach.
This test uses `git annex fsck` to verify the integrity of files. If any file is not validated then the test fails.

### Saving Test Results **(Post Test)**

Once every tests are done, the test suite saves the test results in two location: the CircleCi dashboard and as a CircleCI artifact.
This allows to easily see which test fails.

## Monitoring

Work in progress !

<!-- Dataset still work -->

<!-- Last time dataset worked -->
<!-- Integration in CONP-Portal -->

# Authenticated Dataset

<!-- What should be done prior the tests -->

## Secret creation

<!-- useing project_name2env -->
<!-- Add them into CircleCI/TravisCI -->

## Limitations with secrets

<!-- Limitations -->
<!-- Work around by setting up secret in your personnal CircleCI -->

# Implementation keypoints

## Flaky test

The current test suite cover a broad range of components for dataset to work properly. Unfortunately, there are components that are hard to test in real environment such as downloading files from live servers.
<br/>
For this reason, we opted to allow test to be flaky. That is, when a test fail it will rerun up to 3 times. There is a 5 seconds delay between rerun of failures. Furthermore, to avoid datalad command to conflict during a dataset installation, an instruction to install a dataset will be queue if this dataset is already installing.

## Empty dataset

<!-- No file in annex -->

## Timeout

<!-- CircleCI timeout -->
<!-- Download timeout -->

## Size of Annexed File

Dataset files vary in size.
This can be and issue when testing the download of a dataset as downloading a large file might result in timeout and test failure.
To prevent this problem to happen, the test suite sorts the files based on their size; if a file size cannot be retrieved it sets it to infinity.
Then, it downloads the files in incresing order of their size.
This as the potential to speedup the test suite considerably.
