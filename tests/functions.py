from contextlib import contextmanager
import os
from random import sample
from git import Repo
import signal

import datalad.api as api


@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        pass
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def raise_timeout(signum, frame):
    raise TimeoutError


def examine(dataset):

    # Check if dats.json and README.md are present in root of dataset
    file_names = [file_name for file_name in os.listdir(dataset)]
    if "DATS.json" not in file_names:
        return "Dataset " + dataset + " doesn't contain DATS.json in its root directory"

    if "README.md" not in file_names:
        return "Dataset " + dataset + " doesn't contain README.md in its root directory"

    # Number of files to test in each dataset
    # with 100 files, the test is not completing before Travis timeout (about 10~12 minutes)
    num_files = 4
    
    # Get list of all annexed files and choose randomly num_files of them to test
    files = Repo(dataset).git.annex("list").split("\n____X ")[1:]
    files = sample(files, min(num_files, len(files)))

    # Test those randomly chose files
    error = ""
    for file in files:
        with timeout(3):
            r = api.get(path=os.path.join(dataset, file), on_failure="ignore", return_type="list")

            # Check for authentication
            if r[-1]["status"] == "error" and "unable to access" in r[-1]["message"].lower():
                error = "Cannot download file and didn't hit authentication request for file: {}"\
                    .format(os.path.join(dataset, file))
                break

    if len(error) > 0:
        print("Error is: " + error)
        return False

    return True
