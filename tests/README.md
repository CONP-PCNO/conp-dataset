# CONP dataset - Test suite

### Table of content:

- [Dependencies](#Dependencies)
  - [git-annex](#git-annex)
  - [Python modules](#Python-modules)
- [Executing the Test Suite](#Executing-the-Test-Suite)
- [Test Suite Structure](#Test-Suite-Structure)
  - [Relevant code base components](#Relevant-code-base-components)
- [Life of a Dataset Test](#Life-of-a-Dataset-Test)
  - [Test creation](#Test-creation)
  - [Dataset validation](#Dataset-validation)
- [Authenticated Dataset](#Authenticated-Dataset)
  - [Secrets creation](#Secrets-creation)
  - [Limitations of secrets](#Limitations-of-secrets)
- [Implementation Keypoints](#Implementation-Keypoints)
  - [Flaky test](#Flaky-test)
  - [Empty dataset](#Empty-dataset)
  - [Timeout](#Timeout)
  - [Size of annexed file](#Size-of-annexed-file)

## Dependencies

### git-annex

We recommend using git-annex version 8.20200330 and above.
You can get git-annex binaries or use your package manager ([see here](https://git-annex.branchable.com/install/)).

### Python modules

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
the following command from the repository root to create the environment and
install the locked project and test dependencies:

```bash
uv sync
```

Initialize the script submodules required by schema validation:

```bash
uv run datalad install -r scripts
```

## Executing the Test Suite

Once all dependencies are installed, you will be ready to run the test suite.
You can run them using this command at the root of the repository:

```bash
uv run python tests/create_tests.py
uv run pytest tests/
```

#### Optinal flags

- `-v` : Verbose mode.
- `-s` : Display print statement from in the output.
- `-rfEs` : Show extra summary for (f)ailed, (E)rror, and (s)kipped.
- `-n=N` : Run N tests in parallel.

## Test Suite Structure

### Relevant code base components

```
.
├── scripts
│ ├── Crawlers
│ ├── dats_validator
│ └── unlock.py             # Inject zenodo token into annex urls.
├── tests
│ ├── create_tests.py       # Generate a test file for each dataset, when required.
│ ├── functions.py          # Contains all the utility functions for testing.
│ └── template.py           # Regroup the test methods for dataset.
├── pyproject.toml          # Project and development dependencies.
└── uv.lock                 # Resolved dependency versions.
```

<!-- Utility functions -->
<!-- Template -->
<!-- Test generation -->

## Life of a Dataset Test

This section describes the different steps a dataset test will perform to validate the proper functioning of datasets.

### Test creation

At the start of a test run, the `template.py` file is used to generate a test file for each dataset.
Changes made to a dataset should not influence the behavior of other datasets while changes to the test suite potentially impacts every dataset.
To solve this, the test suite will start by retrieving all files modified during a pull request.
Then, it will only test on the minimal set of datasets.
This strategy aims at saving computing resources as well as time.

To select whether a dataset should be tested or not, we follow this heuristic:

1. File modified is **not** part of a dataset:
   - is part of a whitelist (see below), then **ignore**;
   - otherwise, **full rerun** of the test suite.
1. File is part of a dataset, then **partial rerun** test for this dataset.
1. Outside of pull request, **full rerun** of the test suite.

```
Whitelist
┌─────────────┬────────────────────┐
│ Exact match │ Contains pattern   │
├─────────────┼────────────────────┤
│  .datalad   │  .git              │
│  docs       │  README            │
│  metadata   │  LICENSE           │
│             │  pyproject.toml    │
└─────────────┴────────────────────┘
```

### Dataset validation

During this phase of the test suite, the dataset will be subjected to the different tests below to ensure that their content is valid with the CONP portal convention.
Once a dataset passes the whole test suite, we can be more confident that it will be functional for other users.

#### Datalad install **(Setup)**

This step runs before each test case mentioned below.
To prevent concurrent execution of the command to cause issue, test cases for a dataset are queued when the dataset is already being installed.

#### Has `README.md`

Every dataset is required to have a `README.md` file to describe its content.
This test validates that this file exists.

#### Has a valid `DATS.json` file

Every dataset must have a `DATS.json` that follows that [DATS model convention](https://datatagsuite.github.io/docs/html/dats.html).
This test makes sure that the `DATS.json` file exists and that its content is conformed to the DATS Model.

#### Datalad get

The ability to download a dataset is a critical component for its proper function.
This test goes through the process of downloading files from a dataset to valid its validity.
That is, the test case executes those steps:

1. Authenticate the dataset (see [Authenticated Dataset](#authenticated-dataset) section).
1. (**Travis specific**) Remove files using FTP due to issue on travis; more detail [here](https://blog.travis-ci.com/2018-07-23-the-tale-of-ftp-at-travis-ci).
1. From a sample of n files, the k smallest files are selected. This aims at saving computing resources (see [Timeout](#timeout) and [Size of Annexed File](#size-of-annexed-file) sections).
1. Use `datalad get` to download each of the k files form the sample.

#### Files integrity

Downloading every file in a dataset to assure the proper functioning of a dataset would be rather unpractical, however, verifying the integrity of files is more rational approach.
This test uses `git annex fsck` to verify the integrity of files. If any file is not validated then the test fails.

## Authenticated Dataset

<!-- What should be done prior the tests -->

The test suite supports restricted datasets with authentication through LORIS or Zenodo, but requires the credentials below to be set in the environment before running tests.

### Secrets creation

To generate a standardized \${PROJECT_NAME} for the required environment variables:

```python
from tests.functions import project_name2env

project_name2env("projects/dataset_name".split("/")[-1])
# DATASET_NAME
```

#### Loris

1. Create a LORIS account for testing.
1. Set the following environment variables in the test environment:
   - `${PROJECT_NAME}_USERNAME`
   - `${PROJECT_NAME}_PASSWORD`
   - `${PROJECT_NAME}_LORIS_API`; e.g. `https://example.loris.ca/api/v0.0.0`

#### Zenodo

1.  [Create a new Zenodo token](https://zenodo.org/account/settings/applications/tokens/new/)
1. Set `${PROJECT_NAME}_ZENODO_TOKEN` in the test environment.

### Limitations of secrets

A major limitation of secrets is that authenticated datasets cannot be tested on pull requests due to privacy issues.
Indeed, malicious users could easily retrieve secrets by making a pull requests.

Do not expose credentials to untrusted pull request code. Set credentials only in a trusted, private test environment.

Run authenticated-dataset tests only in a trusted environment with credentials available; do not expose credentials to untrusted pull request code.

## Implementation Keypoints

### Flaky test

The current test suite covers a broad range of components for dataset to work properly. Unfortunately, there are components that are hard to test in real environments such as downloading files from live servers.
<br/>
For this reason, we opted to allow test to be flaky.
That is, when a test fails it will rerun up to 3 times.
There is a 5 seconds delay between rerun of failures.
Furthermore, to avoid DataLad command to conflict during a dataset installation, an instruction to install a dataset will be queued if this dataset is already installing.

### Empty dataset

When a dataset has no file contained in its annex, the test suite assumes the dataset works properly and passes the test.

### Timeout

Since the test suite involves downloading data from external servers, the runtime of the test suite can vary considerably when there is network issues.
To mitigate bad connection to server, the test suite imposes a 5-minute timeout for the validation of files integrity as well as a 2-minute timeout specific for the download of each dataset.

### Size of annexed file

Dataset files vary in size.
This can be an issue when testing the download of a dataset as downloading a large file might result in a timeout and test failure.
To prevent this problem, the test suite sorts the files based on their size; if a file size cannot be retrieved it sets it to infinity.
Then, it downloads the files in increasing order of their size.
This has the potential to speedup the test suite considerably.
