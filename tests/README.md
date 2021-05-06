# CONP dataset - Test suite

[![CircleCI](https://circleci.com/gh/CONP-PCNO/conp-dataset.svg?style=shield)](https://circleci.com/gh/CONP-PCNO/conp-dataset)

### Table of content:

- [Dependencies](#Dependencies)
  - [git-annex](#git-annex)
  - [Python modules](#Python-modules)
- [Executing the Test Suite](#Executing-the-Test-Suite)
- [Test Suite Structure](#Test-Suite-Structure)
  - [Relevant code base components](#Relevant-code-base-components)
  - [CircleCI workflow](#CircleCI-workflow)
- [Life of a Dataset Test](#Life-of-a-Dataset-Test)
  - [Test creation](#Test-creation)
  - [Dataset validation](#Dataset-validation)
  - [Monitoring](#Monitoring)
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
You can get git-annex by using our CircleCI container, getting the latest
binaries, or using your package manager ([see here](https://git-annex.branchable.com/install/)). We favor using our CircleCI container to improve reproducibility of
the test suite.

#### CircleCI container

The latest version of the container used for testing can be obtained from Docker
Hub:

```bash
docker pull mathdugre/conp-dataset:latest
```

#### Dockerfile

The image can also be built directly from our [Dockerfile](https://github.com/CONP-PCNO/conp-dataset/blob/master/.circleci/images/Dockerfile).

```bash
cd conp-dataset/.circleci/images
docker build -t mathdugre/conp-dataset:latest .
```

#### Docker usage

The Docker container can be run using this command:

```bash
docker run -it --name="conp-dataset" mathdugre/conp-dataset:latest
```

For more information on Docker we recommend reading [Docker getting started guide](https://docs.docker.com/get-started/).

### Python modules

To run the test suite you will need to install the project module requirements
for Python. Since there are multiple locations for the _requirements.txt_ files
we recommend using the below command at the root of the repository to install
all the Python dependencies.

```bash
find . -name requirements.txt | xargs -I{} pip install -r {}
```

## Executing the Test Suite

Once all dependencies are installed, you will be ready to run the test suite.
You can run them using this command at the root of the repository:

```bash
python -m venv venv
. venv/bin/activate
PYTHONPATH=$PWD pytest tests/test_*
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

### CircleCI workflow

```
                                               worker x1
                                          ╔════════════════╗
                                          ║     Build      ║
                                          ╠════════════════╣
                                          ║     Python     ║
                                          ║  Dependencies  ║
                                          ╟────────────────╢
                                          ║ DATS validator ║
                                          ╚═══════╤════════╝
        ┌──────────────────◄──────────────────────┘
        │
        ▼
        │                                                    worker x2
┌───────┴───────┐         ┌──────────────────┐         ╔═════════════════╗         ┌───────────────────┐
│ Create Tests  ├────►────┤    Split Tests   ├────►────╢       Test      ╟────►────┤   Tests Results   │
╞═══════════════╡         ╞══════════════════╡         ╠═════════════════╣         ╞═══════════════════╡
│ Generate test │         │ Distribute tests │         ║ datalad_install ║         │ Show on dashboard │
│   files from  │         │  equally amongs  │         ║     (Setup)     ║         ├───────────────────┤
│    Template   │         │     workers      │         ╟─────────────────╢         │ Save to artifacts │
└───────────────┘         └──────────────────┘         ║    has_readme   ║         └─────────┬─────────┘
                                                       ╟─────────────────╢                   │
                                                       ║ has_valid_dats  ║                   │
                                                       ╟─────────────────╢                   │
                                                       ║   datalad_get   ║                   ▼
                                                       ╟─────────────────╢                   │
                                                       ║ files_integrity ║                   │
                                                       ╚═════════════════╝                   │
                                                                                             │
                                                  ┌─────────────────◄────────────────────────┘
                                                  │
                                                  ▼
                                                  │
                                               ╔══╧══╗
                                               ║ END ║
                                               ╚═════╝
```

The workflow is composed of two jobs: build and test.

**Build job:**

- No parallelism.
- Install the dependencies and save them to the workspace for subsequent jobs.

Before test job:<br/>
The test suite is split equally amongs the workers.
This aims at speeding up the tests execution.

**Test job:**

- Parallelism on 2 workers.
- Execute the dataset template test suite.

After test job: (WIP)<br/>
The test results are parsed and saved as a CircleCI artifacts.
Those artifacts are easily accessible through the CircleCI API:

```bash
curl -L https://circleci.com/api/v1.1/project/github/CONP-PCNO/conp-dataset/latest/artifacts?branch=master&filter=completed
```

## Life of a Dataset Test

This section describes the different steps a dataset test will perform to validate the proper functioning of datasets.

### Test creation

At the start of the test job, the `template.py` file is used to generate a test file for each dataset.
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
│             │  requirements.txt  │
└─────────────┴────────────────────┘
```

### Dataset validation

During this phase of the test suite, the dataset will be subjected to the different tests below to ensure that their content is valid with the CONP portal convention.
Once a dataset passes the whole test suite, we can be more confident that it will be functional for other users.

#### Datalad install **(Setup)**

This step runs before every test case mentioned below.
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

#### Saving test results **(Post Test)**

Once every test is completed, the test suite saves the test results in two locations: the CircleCI dashboard and as a CircleCI artifact.
This allows to easily see which test failed.

### Monitoring

To allow users to quickly know if a dataset is properly working at a point in time, we implemented a monitoring system.
Additionally of running the tests when changes occur, we rerun the test suite on the master branch every 4 hours.

The monioring system first retrieve the previous test results, if any.
Then it parses the new test results for each dataset.
When a previous test result exists, it gets updated, otherwise, it is merely added.

The following dataset' components are being monitored for each dataset test:

- `status:` Any of _Success_, _Failure_, _Skipped_, or _Error_
- `Last Passed:` Most recent datetime when the dataset passed the test sucessfully.
- `Runtime:` Execution time of the test.
- `Message:` When not successful, shows information on the source of failure.

e.g.

```
{
    "ProjectName:TestName": {
        "status": "Error",
        "Last passed": "Unknown",
        "Runtime": 0.5,
        "Message": "test setup failure"
    },
    "ProjectName:TestName2": {
        "status": "Success",
        "Last passed": "2020-05-19 12:13:28.342326+00:00",
        "Runtime": 3.2,
        "Message": null
    },

}
```

To quickly retrieve the last test results you can use the following command at the root of the project:

```bash
python -c 'from tests.parse_results import get_previous_test_results; print(get_previous_test_results())'
```

## Authenticated Dataset

<!-- What should be done prior the tests -->

The test suite currently supports restricted dataset with authentication through LORIS or Zenodo, however, it requires prior setup described below. For completing the setup, please contact the CircleCI administrator: Tristan Glatard.

### Secrets creation

To create the secrets in CircleCI you will need to generate a standardized \${PROJECT_NAME} as done below:

```python
from tests.functions import project_name2env

project_name2env("projects/dataset_name".split("/")[-1])
# DATASET_NAME
```

#### Loris

1. Create a LORIS account to be used on CircleCI.
1. Assisted by the CircleCI administrator create the following secrets:
   - `${PROJECT_NAME}_USERNAME`
   - `${PROJECT_NAME}_PASSWORD`
   - `${PROJECT_NAME}_LORIS_API`; e.g. `https://example.loris.ca/api/v0.0.0`

#### Zenodo

1.  [Create a new Zenodo token](https://zenodo.org/account/settings/applications/tokens/new/)
1.  Assisted by the CircleCI administrator, create a secret called `${PROJECT_NAME}_ZENODO_TOKEN`.

### Limitations of secrets

A major limitation of secrets is that authenticated datasets cannot be tested on pull requests due to privacy issues.
Indeed, malicious users could easily retrieve secrets by making a pull requests.

To avoid this problem, the user making a pull request on an authenticated dataset can set up secrets for the dataset in its CircleCI account.

#TODO
Otherwise, the pull requests for authenticated datasets should be merged into a devel branch to assure their proper functioning.
Then, when everything is working, it can be merged into the master branch.

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
