import argparse
import os
from ftplib import FTP


def crawl(host, root, subdir):
    """
    Recursively prints the URLs of the files under dir and adds them to git-annex
    """
    old_dir = ftp.pwd()
    ftp.cwd(os.path.join("/", root, subdir))
    for entry in ftp.mlsd():
        file_name, metadata = entry
        if metadata["type"] == "dir":
            print(f"mkdir -p {file_name}")
            crawl(host, root, os.path.join(subdir, file_name))
        elif metadata["type"] == "file":
            url = f"ftp://{host}/" + os.path.join(root, subdir, file_name)
            local_file_name = os.path.join(subdir, file_name)
            print(f"git-annex addurl {url} --file {local_file_name}")
            os.system(f"git-annex addurl {url} --file {local_file_name}")
    ftp.cwd(old_dir)


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl FTP dataset.")

    parser.add_argument("host", type=str, help="Url of the FTP host.")
    parser.add_argument("directory", type=str, help="Diractory path to the dataset.")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    with FTP(args.host) as ftp:
        ftp.login()
        crawl(args.host, args.directory, "")
