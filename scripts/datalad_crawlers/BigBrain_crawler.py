import os
from ftplib import FTP


host = "bigbrain.loris.ca"
directory = "BigBrainRelease.2015/3D_Surfaces/Apr7_2016"


def crawl(dir):
    """
    Recursively prints the URLs of the files under dir and adds them to git-annex
    """
    old_dir = ftp.pwd()
    ftp.cwd(dir)
    for entry in ftp.mlsd():
        file_name, metadata = entry
        if metadata["type"] == "dir":
            print(f"mkdir -p {file_name}")
            crawl(file_name)
        if metadata["type"] == "file":
            url = f"ftp://{host}/{directory}/{dir}/{file_name}"
            local_file_name = f"{dir}/{file_name}"
            print(f"git-annex addurl {url} --file {local_file_name}")
            os.system(f"git-annex addurl {url} --file {local_file_name}")
    ftp.cwd(old_dir)


ftp = FTP(host)
ftp.login()
crawl(directory)
ftp.quit()
