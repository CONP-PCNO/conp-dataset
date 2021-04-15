import json
import os
from datetime import datetime

import requests
from junitparser import Error
from junitparser import Failure
from junitparser import JUnitXml
from junitparser import Skipped


def get_previous_test_results():
    project_slug = "github/CONP-PCNO/conp-dataset"
    branch = "master"
    url = f"https://circleci.com/api/v1.1/project/{project_slug}/latest/artifacts?branch={branch}&filter=completed"

    artifacts = requests.get(url).json()

    previous_test_results = {}
    for artifact in artifacts:
        # Merge dictionnaries together.
        previous_test_results = {
            **previous_test_results,
            **requests.get(artifact["url"]).json(),
        }

    return previous_test_results


def get_test_case_output(case, previous_test_results):
    dataset = case2datasetname(case)

    if case.result:
        message = case.result.message
        last_passed = (
            previous_test_results[dataset]["Last passed"]
            if dataset in previous_test_results
            else "Unknown"
        )

        if isinstance(case.result, Failure):
            status = "Failure"
        elif isinstance(case.result, Skipped):
            status = "Skipped"
        elif isinstance(case.result, Error):
            status = "Error"
    else:
        message = None
        last_passed = current_time
        status = "Success"

    return {
        "status": status,
        "Last passed": last_passed,
        "Runtime": case.time,
        "Message": message,
    }


def case2datasetname(case):
    return (
        case.classname.replace("tests.test_projects_", "", 1).replace(
            ".TestDataset",
            "",
            1,
        )
        + ":"
        + case.name.replace("test_", "", 1).split("[")[0]
    )


def parse_test_results():
    output_path = os.path.join(os.getcwd(), "tests")
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    previous_test_results = get_previous_test_results()

    # Retrieve new test results.
    with open(os.path.join(output_path, "test-status.json"), "w") as fout:
        xml = JUnitXml.fromfile(os.path.join(output_path, "junit.xml"))

        output_result = {
            case2datasetname(case): get_test_case_output(case, previous_test_results)
            for suite in xml
            for case in suite
            if case.classname.startswith("tests.test_projects_")
        }

        json.dump(
            output_result,
            fout,
            indent=4,
        )


current_time = str(datetime.now().astimezone())
if __name__ == "__main__":
    parse_test_results()
