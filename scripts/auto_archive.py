from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from datetime import timedelta

import git
import humanfriendly
from datalad.plugin import export_archive
from github import Github

from scripts.datalad_utils import get_dataset
from scripts.datalad_utils import install_dataset
from scripts.datalad_utils import uninstall_dataset
from scripts.log import get_logger
from tests.functions import get_proper_submodules


logger = get_logger(
    "CONP-Archive", filename="conp-archive.log", file_level=logging.DEBUG
)


class ArchiveFailed(Exception):
    pass


def parse_args():
    example_text = """Example:
    PYTHONPATH=$PWD python scripts/auto_archive.py <out_dir>
    """

    parser = argparse.ArgumentParser(
        description="Archiver for the CONP-datasets.",
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--out_dir", "-o", type=str, help="Path to store the archived datasets."
    )
    parser.add_argument(
        "--max-size",
        type=float,
        help="Maximum size of dataset to archive in GB.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Archive all the datasets rather than those modified since the last time.",
    )
    group.add_argument(
        "--dataset",
        "-d",
        type=str,
        nargs="+",
        help="Restrict the archive to the specified dataset paths.",
    )

    return parser.parse_args()


def get_datasets_path():
    return {
        os.path.basename(submodule.path): submodule.path
        for submodule in git.Repo().submodules
        if submodule.path.startswith("projects")
    }


def get_modified_datasets(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> set[str]:
    """Retrieve the modified datasets.

    Requires to set GITHUB_ACCESS_TOKEN as an environment variable.

    Parameters
    ----------
    since : Optional[datetime], optional
        Start date from which commits are retrieved, by default date of the previous crawl, if never crawled set to
        one week ago.
    until : Optional[datetime], optional
        Latest date at which commit are retrieved, by default `now`

    Returns
    -------
    set[str]
        Path of the dataset folders.
    """
    now = datetime.now().astimezone()

    if since is None:
        if os.path.exists(".conp-archive"):
            with open(".conp-archive") as fin:
                since = datetime.fromisoformat(fin.read())
        else:
            since = now - timedelta(weeks=1)

    if until is None:
        until = now

    try:
        gh_access_token = os.environ.get("GITHUB_ACCESS_TOKEN", None)
        if gh_access_token is None:
            raise OSError("GITHUB_ACCESS_TOKEN is not defined.")

    except OSError as e:
        # The program is not stopped since GitHub allows 60 query per hours with
        # authentication. However the program will most likely fail.
        logger.critical(e)

    logger.info(f"Retrieving modified datasets since {since}")
    repo = Github(gh_access_token).get_repo("CONP-PCNO/conp-dataset")
    commits = repo.get_commits(since=since, until=until)

    with open(".conp-archive", "w") as fout:
        fout.write(now.isoformat())

    modified_datasets: set[str] = {
        os.path.basename(file_.filename)
        for commit in commits
        for file_ in commit.files
        if file_.filename.startswith("projects/")
    }

    return modified_datasets


def archive_dataset(
    dataset_path: str, out_dir: str, archive_name: str, version: str
) -> None:
    os.makedirs(out_dir, mode=0o755, exist_ok=True)
    out_filename = os.path.join(out_dir, f"{archive_name}_version-{version}.tar.gz")
    logger.info(f"Archiving dataset: {dataset_path} to {out_filename}")

    cwd = os.getcwd()
    try:
        datalad_archiver = export_archive.ExportArchive()
        dataset_repo = git.Repo(dataset_path)

        with open(os.path.join(dataset_path, ".git.log"), "w") as fout:
            fout.write(dataset_repo.git.log(pretty="format:%H %s"))

        # Export is performed from the dataset root.
        # This is to avoid failure when a submodule is not downloaded; e.g. for parent
        # dataset in dataset derivative.
        os.chdir(os.path.join(cwd, dataset_path))
        datalad_archiver(".", filename=out_filename)

    except Exception as e:
        raise ArchiveFailed(
            f"FAILURE: could not archive dataset: {dataset_path} to {out_filename}\n{e}"
        )
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    args = parse_args()

    # Only archive the datasets available locally.
    datasets_path = get_datasets_path()
    datasets = datasets_path.keys()
    if args.dataset:
        target_datasets = {os.path.basename(os.path.normpath(d)) for d in args.dataset}
        logger.warning(
            f"The following dataset were not found locally: {target_datasets - datasets}"
        )
        datasets &= target_datasets

    elif not args.all:
        modified_datasets = get_modified_datasets()
        logger.warning(
            f"The following dataset were not found locally: {modified_datasets - datasets}"
        )
        datasets &= modified_datasets

    for dataset_name in datasets:
        dataset = datasets_path[dataset_name]

        try:
            logger.info(f"Installing dataset: {dataset}")
            install_dataset(dataset)

            is_public = False
            version = ""
            dataset_size = 0.0

            with open(os.path.join(dataset, "DATS.json")) as fin:
                metadata = json.load(fin)

                is_public = (
                    metadata.get("distributions", [{}])[0]
                    .get("access", {})
                    .get("authorizations", [{}])[0]
                    .get("value")
                    == "public"
                )
                version = metadata.get("version")

                for distribution in metadata.get("distributions", list()):
                    dataset_size += humanfriendly.parse_size(
                        f"{distribution['size']} {distribution['unit']['value']}",
                    )
                    dataset_size //= 1024 ** 3  # Convert to GB

            # Only archive public dataset less than a specific size if one is provided to the script
            if is_public:
                if args.max_size is None or dataset_size <= args.max_size:
                    logger.info(f"Downloading dataset: {dataset}")
                    get_dataset(dataset)
                    for submodule in get_proper_submodules(dataset):
                        get_dataset(submodule)

                    archive_name = "__".join(
                        os.path.relpath(dataset, "projects").split("/")
                    )
                    archive_dataset(
                        dataset,
                        out_dir=args.out_dir,
                        archive_name=archive_name,
                        version=version,
                    )
                    # to save space on the VM that archives the dataset, need to uninstall
                    # the datalad dataset. `datalad drop` does not free up enough space
                    # unfortunately. See https://github.com/datalad/datalad/issues/6009
                    uninstall_dataset(dataset)
                    logger.info(f"SUCCESS: archive created for {dataset}")
                else:
                    logger.info(f"SKIPPED: {dataset} larger than {args.max_size} GB")
            else:
                logger.info(
                    f"SKIPPED: archive not needed for {dataset}. Non-public dataset."
                )

        except Exception as e:
            # TODO implement notification system.
            # This will alert when a dataset fails the archiving process.
            logger.exception(
                f"FAILURE: could not archive dataset: {dataset} to {args.out_dir}.tar.gz\n{e}"
            )

    logger.info("Done archiving the datasets.")
