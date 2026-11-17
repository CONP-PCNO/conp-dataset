"""Regression tests for the tracked dataset filename checker."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from check_dataset_filenames import find_findings, main, run_check


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "core.ignorecase", "false")
    _git(repo, "config", "user.name", "Portability tests")
    _git(repo, "config", "user.email", "portability-tests@example.invalid")


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)


def _index_file(repo: Path, path: str, content: str) -> None:
    blob = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input=content,
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()
    _git(repo, "update-index", "--add", "--cacheinfo", "100644", blob, path)


def test_finds_case_and_directory_collisions() -> None:
    findings = find_findings(["Data/scan.nii", "data/other.nii", "Report.TXT", "report.txt"], ".")

    assert {
        finding.category
        for finding in findings
        if finding.path_a in {"Data/scan.nii", "Report.TXT"} or finding.path_b in {"Data/scan.nii", "Report.TXT"}
    } == {"case-insensitive"}
    assert any(
        finding.category == "case-insensitive"
        and {finding.path_a, finding.path_b} == {"Data/scan.nii", "data/other.nii"}
        for finding in findings
    )


def test_finds_unicode_normalization_collision() -> None:
    findings = find_findings(["caf\u00e9.txt", "cafe\u0301.txt"], "projects/sample")

    assert len(findings) == 1
    finding = next(iter(findings))
    assert finding.category == "unicode-normalization"
    assert finding.location == "projects/sample"


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("CON.txt", "reserved Windows device name"),
        ("scan. ", "trailing spaces or periods"),
        ("bad:name", "character forbidden"),
    ],
)
def test_finds_windows_incompatible_components(path: str, detail: str) -> None:
    findings = find_findings([path], ".")

    assert len(findings) == 1
    assert detail in next(iter(findings)).detail


def test_existing_findings_do_not_block_unrelated_changes(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "catalogue"
    _init_repo(repo)
    _index_file(repo, "Name.txt", "one")
    _index_file(repo, "name.txt", "two")
    _git(repo, "commit", "-qm", "add existing collision")
    (repo / "README.md").write_text("unrelated change")

    result = run_check(
        repo,
        base_ref=None,
        strict_submodules=False,
        fetch_missing_base=False,
    )

    assert result == 0
    assert "BASELINE:" in capsys.readouterr().out


def test_new_root_collision_fails(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "catalogue"
    _init_repo(repo)
    (repo / "scan.nii").write_text("one")
    _commit(repo, "add baseline file")
    _index_file(repo, "SCAN.nii", "two")

    result = run_check(
        repo,
        base_ref=None,
        strict_submodules=False,
        fetch_missing_base=False,
    )

    assert result == 1
    assert "new filename portability issue" in capsys.readouterr().out


def test_new_conflict_in_changed_subdataset_is_checked_at_pinned_commit(tmp_path: Path, capsys) -> None:
    origin = tmp_path / "dataset-origin"
    _init_repo(origin)
    (origin / "scan.nii").write_text("one")
    _commit(origin, "baseline dataset")

    root = tmp_path / "catalogue"
    _init_repo(root)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(origin),
            "projects/sample",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    _commit(root, "add dataset")

    child = root / "projects/sample"
    _git(child, "config", "core.ignorecase", "false")
    _index_file(child, "SCAN.nii", "two")
    _git(child, "commit", "-qm", "add conflicting filename")
    _git(root, "add", "projects/sample")

    result = run_check(
        root,
        base_ref=None,
        strict_submodules=True,
        fetch_missing_base=False,
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "projects/sample" in output
    assert "case-insensitive" in output


def test_missing_pinned_subdataset_is_an_explicit_failure(tmp_path: Path, capsys) -> None:
    origin = tmp_path / "dataset-origin"
    _init_repo(origin)
    (origin / "README.md").write_text("dataset")
    _commit(origin, "dataset")

    root = tmp_path / "catalogue"
    _init_repo(root)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(origin),
            "projects/sample",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    _commit(root, "add dataset")
    (root / "projects/sample").rename(tmp_path / "checked-out-elsewhere")

    result = main(["--root", str(root), "--strict-submodules"])

    assert result == 2
    assert "not initialized" in capsys.readouterr().err
