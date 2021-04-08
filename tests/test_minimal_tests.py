"""Test the minimalTest function in create_tests.py.

This function should return the minimal set of test to execute.
"""
import git
import pytest

from tests.create_tests import minimal_tests


@pytest.fixture(autouse=True)
def retrieve_submodule():
    """Fixture to get all the CONP datasets before a test."""
    pytest.datasets = {x.path for x in git.Repo(".").submodules}
    yield


@pytest.mark.parametrize("pr_files", [[]])
def test_empty_pr(pr_files):
    """Test pull requests that modify no file."""
    assert minimal_tests(pytest.datasets, pr_files) == []


@pytest.mark.parametrize(
    "pr_files",
    [("projects/preventad-open",), ("projects/PERFORM_Dataset__one_control_subject",)],
)
def test_modify_single_project(pr_files):
    """Test pull requests that modify a single project."""
    pr_files = list(pr_files)
    assert minimal_tests(pytest.datasets, pr_files) == pr_files


@pytest.mark.parametrize(
    "pr_files",
    [
        ("projects/preventad-open", "projects/PERFORM_Dataset__one_control_subject"),
        ("projects/openpain/BrainNetworkChange_Mano", "projects/preventad-open"),
    ],
)
def test_modify_multi_project(pr_files):
    """Test pull requests that modify multiple project."""
    pr_files = list(pr_files)
    assert minimal_tests(pytest.datasets, pr_files) == pr_files


@pytest.mark.parametrize(
    "pr_files, valid",
    [
        (("projects/preventad-open", "README.md"), ("projects/preventad-open",)),
        (("LICENSE",), []),
    ],
)
def test_modify_whitelist(pr_files, valid):
    """Test pull requests that modify a file in the exact whitelist."""
    pr_files = list(pr_files)
    valid = list(valid)
    assert minimal_tests(pytest.datasets, pr_files) == valid


@pytest.mark.parametrize(
    "pr_files, valid",
    [
        (("projects/preventad-open", ".datalad"), ("projects/preventad-open",)),
        (("metadata/examples",), []),
    ],
)
def test_modify_whitelist_exact(pr_files, valid):
    """Test pull requests that modify a file in the whitelist."""
    pr_files = list(pr_files)
    valid = list(valid)
    assert minimal_tests(pytest.datasets, pr_files) == valid


@pytest.mark.parametrize(
    "pr_files",
    [
        (".travis.yml", "projects/preventad-open", "README.md"),
        ("tests/functions.py", "projects/preventad-open"),
        ("scripts/crawl_zenodo.py",),
    ],
)
def test_run_all(pr_files):
    """Test pull request that need to execute all tests."""
    pr_files = list(pr_files)
    assert minimal_tests(pytest.datasets, pr_files) == pytest.datasets
