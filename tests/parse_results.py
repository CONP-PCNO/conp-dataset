from datetime import datetime
import json
import os

from junitparser import JUnitXml, Failure, Skipped, Error


def parse_test_results():
    current_time = str(datetime.now().astimezone())
    output_path = os.path.join(os.getcwd(), "tests")

    try:
        with open(os.path.join(output_path, "tests-status.json")) as fin:
            prev_test_result = json.load(fin)
    except Exception as e:
        prev_test_result = {}

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
