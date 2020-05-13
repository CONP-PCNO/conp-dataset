from datetime import datetime
import json
import os

from junitparser import JUnitXml, Failure, Skipped, Error
import requests


def get_previous_test_results():
    project_slug = "github/mathdugre/conp-dataset"
    branch = "monitoring"
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


def parse_test_results():
    current_time = str(datetime.now().astimezone())

    output_path = os.path.join(os.getcwd(), "tests")
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    previous_test_results = get_previous_test_results()

    # Register new test results.
    with open(os.path.join(output_path, "test-status.json"), "w") as fout:
        output_result = {}

        xml = JUnitXml.fromfile(os.path.join(output_path, "junit.xml"))
        for suite in xml:
            for case in suite:
                if not case.classname.startswith("tests.test_projects_"):
                    continue

                dataset = "".join(case.classname.split(".")[1:-1])
                runtime = case.time

                if case.result:
                    message = case.result.message
                    last_passed = (
                        prev_test_result[dataset]["Last passed"]
                        if dataset in prev_test_result
                        else "Never passed"
                    )

                    if isinstance(case.result, Failure):
                        status = "Failure"
                    elif isinstance(case.result, Skipped):
                        status = "Skipped"
                    elif isinstance(case.result, Error):
                        status = "Error"
                else:
                    status = "Success"
                    message = None
                    last_passed = current_time

                output_result[dataset] = {
                    "status": status,
                    "Last passed": last_passed,
                    "Runtime": runtime,
                    "Message": message,
                }

        json.dump(
            output_result, fout, indent=4,
        )


if __name__ == "__main__":
    parse_test_results()
