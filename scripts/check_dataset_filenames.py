#!/usr/bin/env python3
"""Check tracked dataset paths for cross-platform filename incompatibilities."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

WINDOWS_FORBIDDEN = set('<>:"/\\|?*')
WINDOWS_RESERVED = {
    "aux",
    "con",
    "conin$",
    "conout$",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
    *(f"com{number}" for number in "¹²³"),
    *(f"lpt{number}" for number in "¹²³"),
}
GITLINK_MODE = b"160000"


class CheckError(Exception):
    """Raised when a repository or one of its tracked trees cannot be inspected."""


@dataclass(frozen=True, order=True)
class Finding:
    category: str
    location: str
    path_a: str
    path_b: str = ""
    detail: str = ""

    def format(self) -> str:
        paths = f"{self.path_a!r}"
        if self.path_b:
            paths += f" and {self.path_b!r}"
        suffix = f": {self.detail}" if self.detail else ""
        return f"{self.location!r}: {paths} [{self.category}]{suffix}"


@dataclass(frozen=True)
class TreeEntry:
    mode: bytes
    object_id: str
    path: str


def git(repo: Path, *args: str, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        error = os.fsdecode(result.stderr).strip()
        raise CheckError(f"git {' '.join(args)} failed in {repo}: {error}")
    return result.stdout


def _parse_tree_records(output: bytes, *, index: bool = False) -> list[TreeEntry]:
    entries = []
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", maxsplit=1)
            fields = metadata.split()
            if index:
                mode, object_id, stage = fields
                if stage != b"0":
                    raise CheckError(f"unmerged index entry: {os.fsdecode(raw_path)!r}")
            else:
                mode, _object_type, object_id = fields
        except ValueError as error:
            raise CheckError(f"could not parse Git tree entry: {record!r}") from error
        entries.append(TreeEntry(mode, object_id.decode("ascii"), os.fsdecode(raw_path)))
    return entries


def current_entries(repo: Path) -> list[TreeEntry]:
    return _parse_tree_records(git(repo, "ls-files", "--stage", "-z"), index=True)


def tree_entries(repo: Path, revision: str) -> list[TreeEntry]:
    return _parse_tree_records(git(repo, "ls-tree", "-r", "-z", "--full-tree", revision))


def _windows_problem(component: str) -> str | None:
    if component.endswith((" ", ".")):
        return "Windows does not preserve trailing spaces or periods"
    if any(char in WINDOWS_FORBIDDEN or ord(char) < 32 for char in component):
        return "contains a character forbidden in Windows filenames"
    device_stem = component.rstrip(" .").split(".", maxsplit=1)[0].rstrip(" .").casefold()
    if device_stem in WINDOWS_RESERVED:
        return "uses a reserved Windows device name"
    return None


def find_findings(paths: list[str], location: str) -> set[Finding]:
    findings: set[Finding] = set()
    components_by_parent: dict[tuple[str, ...], dict[str, dict[str, tuple[str, str]]]] = {}

    for path in paths:
        components = path.split("/")
        normalized_parent: tuple[str, ...] = ()
        prefix: list[str] = []
        for component in components:
            prefix.append(component)
            full_path = "/".join(prefix)
            problem = _windows_problem(component)
            if problem:
                findings.add(Finding("windows-incompatible", location, path, detail=problem))
            # Group spellings that Windows may treat as the same name.
            component_key = unicodedata.normalize("NFC", component).casefold()
            siblings = components_by_parent.setdefault(normalized_parent, {})
            siblings.setdefault(component_key, {})[component] = (
                full_path,
                path,
            )
            normalized_parent += (component_key,)

    for siblings in components_by_parent.values():
        for spellings in siblings.values():
            values = list(spellings.items())
            for index, (name_a, (_prefix_a, path_a)) in enumerate(values):
                for name_b, (_prefix_b, path_b) in values[index + 1 :]:
                    if name_a == name_b:
                        continue
                    normalized_a = unicodedata.normalize("NFC", name_a)
                    normalized_b = unicodedata.normalize("NFC", name_b)
                    category = "unicode-normalization" if normalized_a == normalized_b else "case-insensitive"
                    first, second = sorted((path_a, path_b))
                    findings.add(Finding(category, location, first, second))
    return findings


def gitlinks(entries: list[TreeEntry]) -> dict[str, str]:
    return {entry.path: entry.object_id for entry in entries if entry.mode == GITLINK_MODE}


def ensure_commit(repo: Path, revision: str, *, fetch: bool) -> None:
    exists = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{revision}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if exists.returncode == 0:
        return
    if not fetch:
        raise CheckError(f"baseline commit {revision} is unavailable in {repo}")
    git(repo, "fetch", "--no-tags", "origin", revision)
    verified = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{revision}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if verified.returncode:
        raise CheckError(f"fetch completed but baseline commit {revision} is unavailable in {repo}")


def _head(repo: Path) -> str:
    return os.fsdecode(git(repo, "rev-parse", "HEAD")).strip()


def _relative_location(parent: str, child: str) -> str:
    return child if parent == "." else f"{parent}/{child}"


def inspect_repository(
    repo: Path,
    location: str,
    current: list[TreeEntry],
    baseline: list[TreeEntry] | None,
    *,
    strict_submodules: bool,
    fetch_missing_base: bool,
    findings: set[Finding],
    baseline_findings: set[Finding],
    incomplete: list[str],
) -> None:
    current_findings = find_findings([entry.path for entry in current], location)
    findings.update(current_findings)
    if baseline is not None:
        baseline_findings.update(
            find_findings(
                [entry.path for entry in baseline],
                location,
            )
        )

    baseline_links = gitlinks(baseline or [])
    for subpath, expected_commit in sorted(gitlinks(current).items()):
        child_location = _relative_location(location, subpath)
        child_repo = repo / subpath
        if not child_repo.is_dir():
            message = f"{child_location!r}: subdataset checkout is not initialized"
            if strict_submodules:
                raise CheckError(message)
            incomplete.append(message)
            continue

        try:
            actual_head = _head(child_repo)
        except CheckError as error:
            if strict_submodules:
                raise
            incomplete.append(f"{child_location!r}: subdataset checkout is not usable ({error})")
            continue
        if actual_head != expected_commit:
            message = (
                f"{child_location!r}: checked-out commit {actual_head} does not match pinned gitlink {expected_commit}"
            )
            if strict_submodules:
                raise CheckError(message)
            incomplete.append(message)
            continue

        current_child = current_entries(child_repo)
        baseline_commit = baseline_links.get(subpath)
        if baseline_commit is None:
            baseline_child = None
        else:
            ensure_commit(child_repo, baseline_commit, fetch=fetch_missing_base)
            baseline_child = tree_entries(child_repo, baseline_commit)
        inspect_repository(
            child_repo,
            child_location,
            current_child,
            baseline_child,
            strict_submodules=strict_submodules,
            fetch_missing_base=fetch_missing_base,
            findings=findings,
            baseline_findings=baseline_findings,
            incomplete=incomplete,
        )


def run_check(
    root: Path,
    *,
    base_ref: str | None,
    strict_submodules: bool,
    fetch_missing_base: bool,
) -> int:
    root = root.resolve()
    current = current_entries(root)
    baseline_revision = base_ref or "HEAD"
    ensure_commit(root, baseline_revision, fetch=False)
    baseline = tree_entries(root, baseline_revision)

    findings: set[Finding] = set()
    baseline_findings: set[Finding] = set()
    incomplete: list[str] = []
    inspect_repository(
        root,
        ".",
        current,
        baseline,
        strict_submodules=strict_submodules,
        fetch_missing_base=fetch_missing_base,
        findings=findings,
        baseline_findings=baseline_findings,
        incomplete=incomplete,
    )

    new_findings = findings - baseline_findings
    existing_findings = findings & baseline_findings
    for finding in sorted(new_findings):
        print(f"ERROR: {finding.format()}")
    for finding in sorted(existing_findings):
        print(f"BASELINE: {finding.format()}")
    for message in incomplete[:10]:
        print(f"INCOMPLETE: {message}")
    if len(incomplete) > 10:
        print(f"INCOMPLETE: {len(incomplete) - 10} additional subdataset(s) were not inspected.")

    if new_findings:
        print(f"Found {len(new_findings)} new filename portability issue(s).")
        return 1
    if incomplete:
        print(
            "No new issues were found in inspected repositories, but this scan is "
            "incomplete; CI performs the authoritative recursive check."
        )
        return 0
    if existing_findings:
        print(f"No new issues; {len(existing_findings)} existing issue(s) are reported above.")
    else:
        print("PASS: no new filename portability issues.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="superdataset checkout")
    parser.add_argument(
        "--base-ref",
        help="baseline root commit (GitHub Actions uses the PR base commit; defaults to HEAD)",
    )
    parser.add_argument(
        "--strict-submodules",
        action="store_true",
        help="fail if any pinned subdataset is missing or checked out at another commit",
    )
    parser.add_argument(
        "--fetch-missing-base",
        action="store_true",
        help="fetch unavailable baseline commits from each subdataset's origin",
    )
    args = parser.parse_args(argv)
    try:
        return run_check(
            args.root,
            base_ref=args.base_ref,
            strict_submodules=args.strict_submodules,
            fetch_missing_base=args.fetch_missing_base,
        )
    except CheckError as error:
        print(
            f"ERROR: filename portability check could not complete: {error}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
