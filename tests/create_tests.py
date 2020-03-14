import os
import re
from string import Template

from git import Repo


def project_name2env(project_name: str) -> str:
    """Convert the project name to a valid ENV var name.

    The ENV name for the project must match the regex `[a-zA-Z_]+[a-zA-Z0-9_]*`.

    Parameters
    ----------
    project_name: str
        Name of the project.

    Return
    ------
    project_env: str
        A valid ENV name for the project.
    """
    project_name = project_name.replace("-", "_")
    project_env = re.sub("[_]+", "_", project_name)  # Remove consecutive `_`
    project_env = re.sub("[^a-zA-Z0-9_]", "", project_env)

    # Env var cannot start with number
    if re.compile("[0-9]").match(project_env[0]):
        project_env = "_" + project_env

    return project_env.upper()


submodules = list(map(lambda x: x.path, Repo(".").submodules))

template = Template(
    """from functions import examine


def test_$clean_title():
    assert examine('$path', '$project')
"""
)

for dataset in submodules:
    if dataset.split("/")[0] == "projects" or dataset.split("/")[0] == "investigators":
        with open("tests/test_" + dataset.replace("/", "_") + ".py", "w") as f:

            dataset_path = os.path.join(
                os.getenv("TRAVIS_BUILD_DIR", os.getcwd()), dataset
            )
            f.write(
                template.substitute(
                    path=dataset_path,
                    project=project_name2env(dataset.split("/")[-1]),
                    clean_title=dataset.replace("/", "_").replace("-", "_"),
                )
            )
