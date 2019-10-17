from string import Template
from git import Repo
from os.path import isfile, join


submodules = list(map(lambda x: x.path, Repo(".").submodules))
changed_submodules = set()

if isfile("tests/diff.txt"):
    with open("tests/diff.txt", "r") as f:
        changes = f.readlines()

    changed_submodules = {submodule for submodule in submodules for line in changes if submodule in line}

    if len(changed_submodules) == 0:
        print("No changes in submodules")
else:
    print("No diff.txt file detected, creating tests for every submodule")
    changed_submodules = set(submodules)


template = Template("""from functions import examine


def test_$clean_title():
    assert examine('$path') == 'All good'
""")

for submodule in changed_submodules:
    test_file = "test_" + submodule.replace("/", "_") + ".py"
    print("Creating " + test_file)
    with open(join("tests", test_file), "w") as f:

        f.write(template.substitute(path=submodule,
                                    clean_title=submodule.replace("/", "_").replace("-", "_")))
