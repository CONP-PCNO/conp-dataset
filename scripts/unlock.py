#!/usr/bin/env python
import json
import os
import re
import traceback

from datalad import api
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


def unlock():
    repo = Repo()
    project: str = project_name2env(repo.working_dir.split("/")[-1])
    token: (str | None) = os.getenv(project + "_ZENODO_TOKEN", None)

    if not token:
        raise Exception(
            f"{project}_ZENODO_TOKEN not found. Cannot inject the Zenodo token into the git-annex urls.",
        )

    annex = repo.git.annex
    if repo.active_branch.name != "master":
        raise Exception("Dataset repository not set to branch 'master'")

    if not os.path.isfile(".conp-zenodo-crawler.json"):
        raise Exception("'.conp-zenodo-crawler.json file not found")

    with open(".conp-zenodo-crawler.json") as f:
        metadata = json.load(f)

    # Ensure correct data
    if not metadata["restricted"]:
        raise Exception("Dataset not restricted, no need to unlock")
    if (
        len(metadata["private_files"]["archive_links"]) == 0
        and len(metadata["private_files"]["files"]) == 0
    ):
        raise Exception("No restricted files to unlock")

    # Set token in archive link URLs
    if len(metadata["private_files"]["archive_links"]) > 0:
        repo.git.checkout("git-annex")
        changes = False
        for link in metadata["private_files"]["archive_links"]:
            for dir_name, _, files in os.walk("."):
                for file_name in files:
                    file_path = os.path.join(dir_name, file_name)
                    if ".git" in file_path:
                        continue
                    with open(file_path) as f:
                        s = f.read()
                    if link in s and "access_token" not in s:
                        changes = True
                        s = s.replace(link, link + "?access_token=" + token)
                        with open(file_path, "w") as f:
                            f.write(s)
        if changes:
            repo.git.add(".")
            repo.git.commit("-m", "Unlock dataset")
        repo.git.checkout("master")

    # Set token in non-archive link URLs
    if len(metadata["private_files"]["files"]) > 0:
        datalad = api.Dataset(".")
        for file in metadata["private_files"]["files"]:
            annex("rmurl", file["name"], file["link"])
            annex(
                "addurl",
                file["link"] + "?access_token=" + token,
                "--file",
                file["name"],
                "--relaxed",
            )
            datalad.save()

    print("Done")


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    try:
        unlock()
    except Exception:
        traceback.print_exc()
    finally:
        # Always switch branch back to master
        repository = Repo()
        if repository.active_branch.name != "master":
            repository.git.checkout("master", "-f")
