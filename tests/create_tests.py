from os import listdir
from string import Template


dataset_titles = list(filter(lambda x: x[0] != ".", listdir("projects") + listdir("investigators")))

template = Template("""from functions import examine


def test_$title_no_hyphen():
    assert examine('$title') == 'All good'
""")

for title in dataset_titles:
    with open("tests/test_" + title + ".py", "w") as f:

        f.write(template.substitute(title=title, title_no_hyphen=title.replace("-", "_")))
