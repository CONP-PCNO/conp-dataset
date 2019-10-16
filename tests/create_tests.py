from string import Template
from git import Repo
from os.path import isfile


submodules = list(map(lambda x: x.path, Repo(".").submodules))
changed_submodules = set()

if isfile("tests/diff.txt"):
    with open("tests/diff.txt", "r") as f:
        changes = f.readlines()

    for line in changes:
        for submodule in submodules:
            if submodule in line:
                changed_submodules.add(submodule)

    if len(changed_submodules) > 0:
        print("Detected changes in the following submodules, creating tests for them:")
        for submodule in changed_submodules:
            print(submodule)
    else:
        print("No changes in submodules")
else:
    print("No diff.txt file detected, creating tests for every submodule")
    changed_submodules = set(submodules)


template = Template("""from functions import examine


def test_$clean_title():
    assert examine('$path') == 'All good'
""")

for submodule in changed_submodules:
    with open("tests/test_" + submodule.replace("/", "_") + ".py", "w") as f:

        f.write(template.substitute(path=submodule,
                                    clean_title=submodule.replace("/", "_").replace("-", "_")))
