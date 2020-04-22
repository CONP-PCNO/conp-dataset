"""Template to base the test of the datasets.
"""


class Template(object):

    def test_has_readme(self, dataset):
        raise NotImplemented

    def test_has_valid_dats(self, dataset):
        raise NotImplemented


    def test_download(self, dataset):
        raise NotImplemented


    def test_files_integrity(self, dataset):
        raise NotImplemented
