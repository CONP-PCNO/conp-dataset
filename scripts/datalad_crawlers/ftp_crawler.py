import argparse
import os
from ftplib import FTP

import git
from tqdm import tqdm


def crawl(host, root, subdir, *, ftp):
    """
    Recursively prints the URLs of the files under dir and adds them to git-annex
    """
    cwd = os.path.join("/", root, subdir)
    print(f"\nCrawling {cwd}")

    for filename, metadata in tqdm(ftp.mlsd(cwd)):
        filepath = os.path.join(subdir, filename)

        while True:
            try:
                if metadata.get("type") == "dir":
                    crawl(host, root, filepath, ftp=ftp)

                elif metadata.get("type") == "file":
                    git.Repo().git.annex(
                        "addurl",
                        f"ftp://{host}/" + os.path.join(cwd, filename),
                        file=filepath,
                    )
                break

            except Exception as e:
                print(f"WARNING: Connection restarted on file: {filepath}: {e}")
                ftp.connect()
                ftp.login()


def parse_args():
    example_text = """Example:
    python /path/to/ftp_crawler.py $FTP_HOST $FTP_DIR

    This will recursively annex the URL of all files from the $FTP_DIR on the $FTP_HOST
    in the git-annex of the current directory.
    """

    parser = argparse.ArgumentParser(
        description="Datalad crawler to crawl FTP server.",
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("host", type=str, help="URL of the FTP host.")
    parser.add_argument("directory", type=str, help="Directory path to the dataset.")
    parser.add_argument(
        "sub_directory", nargs="?", type=str, default="", help="Subdirectory to crawl."
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    with FTP(args.host) as ftp:
        ftp.login()
        crawl(args.host, args.directory, args.sub_directory, ftp=ftp)
