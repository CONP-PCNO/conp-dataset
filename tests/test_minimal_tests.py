"""Test the minimalTest function in create_tests.py.

This function should return the minimal set of test to execute.
"""
import git
import pytest

from .create_tests import minimal_tests


@pytest.fixture(autouse=True)
def retrieve_submodule():
    """Fixture to get all the CONP datasets before a test."""
    pytest.datasets = {x.path for x in git.Repo(".").submodules}
    yield


def test_empty_pr():
    """Test pull requests that modify no file."""
    pass


def test_modify_single_project():
    """Test pull requests that modify a single project."""
    pass


def test_modify_multi_project():
    """Test pull requests that modify multiple project."""
    pass


def test_modify_whitelist():
    """Test pull requests that modify a file in the exact whitelist."""
    pass


def test_modify_whitelist_exact():
    """Test pull requests that modify a file in the whitelist."""
    pass


def test_run_all():
    """Test pull request that need to execute all tests."""
    pass
