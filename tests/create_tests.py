from string import Template
from git import Repo


submodules = list(map(lambda x: x.path, Repo(".").submodules))

template = Template("""from functions import examine


def test_$clean_title():
    assert examine('$path') == 'All good'
""")

for dataset in submodules:
    if dataset.split("/")[0] == "projects" or dataset.split("/")[0] == "investigators":
        with open("tests/test_" + dataset.replace("/", "_") + ".py", "w") as f:

            f.write(template.substitute(path=dataset,
                                        clean_title=dataset.replace("/", "_").replace("-", "_")))
