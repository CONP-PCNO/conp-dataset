import os
import datalad.api as api


def recurse(directory):

    # Get all file names in directory
    files = os.listdir(directory)

    # Loop throw every file
    for file in files:

        # If the file starts with ".", has descriptor or readme in filename, continue onto next file
        if file[0] == "." or \
           "descriptor" in file.lower() or \
           "readme" in file.lower():
            continue

        full_path = os.path.join(directory, file)

        # If the file is a directory
        if os.path.isdir(full_path):

            recurse(full_path)

        # If the file is a broken symlink
        elif not os.path.exists(full_path):
            msg = api.get(path=full_path, on_failure="ignore", return_type="item-or-list")

            # Check for URL in each file
            assert "URL" in msg["annexkey"], "No URL in annexkey: " + msg["annexkey"]


recurse(os.path.abspath("../projects"))
