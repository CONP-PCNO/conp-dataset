import os


dataset_titles = list(filter(lambda x: x[0] != ".", os.listdir("projects") + os.listdir("investigators")))

for title in dataset_titles:
    with open("tests/test_" + title + ".py", "w") as f:
        f.write("from functions import examine\n\n\n")
        f.write("def test_" + title.replace("-", "_") + "():\n")
        f.write("\tassert examine('" + title + "') == 'All good'\n")
