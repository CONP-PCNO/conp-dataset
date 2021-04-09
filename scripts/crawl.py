import argparse
import json
import os
import sys
import traceback

from git import Repo


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=r"""
    CONP crawler.

    Requirements:
    * GitHub user must have a fork of https://github.com/CONP-PCNO/conp-dataset
    * Script must be run in the base directory of a local clone of this fork
    * Git remote 'origin' of local Git clone must point to that fork. Warning: this script will
       push dataset updates to 'origin'.
    * Local Git clone must be set to branch 'master'
    """,
    )
    parser.add_argument(
        "github_token",
        action="store",
        nargs="?",
        help="GitHub access token",
    )
    parser.add_argument(
        "config_path",
        action="store",
        nargs="?",
        help="Path to config file to use",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug information",
    )
    parser.add_argument("--force", action="store_true", help="Force updates")
    parser.add_argument(
        "--no_pr",
        action="store_true",
        help="Don't create a pull request at the end",
    )
    args = parser.parse_args()

    github_token = args.github_token
    config_path = args.config_path
    if not config_path:
        config_path = os.path.join(
            os.path.expanduser("~"),
            ".conp_crawler_config.json",
        )

    # If config file does not exist, create an empty one
    if not os.path.isfile(config_path):
        with open(config_path, "w") as f:
            json.dump({}, f)

    with open(config_path) as f:
        config = json.load(f)

    if "conp-dataset_path" not in config.keys():
        raise Exception(
            '"conp-dataset_path" not configured in ' + config_path + ","
            "please configure it as follows: \n"
            '  "conp-dataset_path": "PATH TO conp-dataset DIRECTORY",',
        )

    if not github_token and "github_token" not in config.keys():
        raise Exception(
            "Github token not passed by command line argument "
            "nor found in config file " + config_path + ", "
            "please pass your github access token via the command line",
        )
    elif github_token:
        config["github_token"] = github_token
        # Store newly passed github token into config file
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
    else:  # Retrieve github token from config file
        github_token = config["github_token"]

    return (
        github_token,
        config_path,
        args.verbose,
        args.force,
        config["conp-dataset_path"],
        args.no_pr,
    )


if __name__ == "__main__":
    (
        github_token,
        config_path,
        verbose,
        force,
        conp_dataset_dir_path,
        no_pr,
    ) = parse_args()

    # import the crawler packages
    sys.path.append(conp_dataset_dir_path)
    from scripts.Crawlers.ZenodoCrawler import ZenodoCrawler
    from scripts.Crawlers.OSFCrawler import OSFCrawler

    try:
        if verbose:
            print(
                "==================== Zenodo Crawler Running ===================="
                + os.linesep,
            )
        ZenodoCrawlerObj = ZenodoCrawler(
            github_token,
            config_path,
            verbose,
            force,
            no_pr,
        )
        ZenodoCrawlerObj.run()

        if verbose:
            print(
                os.linesep
                + "==================== OSF Crawler Running ===================="
                + os.linesep,
            )
        OSFCrawlerObj = OSFCrawler(github_token, config_path, verbose, force, no_pr)
        OSFCrawlerObj.run()

        # INSTANTIATE NEW CRAWLERS AND RUN HERE

    except Exception:
        traceback.print_exc()
    finally:
        # Always switch branch back to master
        repository = Repo()
        if repository.active_branch.name != "master":
            repository.git.checkout("master")

        if verbose:
            print(os.linesep + "==================== Done ====================")
