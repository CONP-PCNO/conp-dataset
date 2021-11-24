from __future__ import annotations

import functools
import os

import datalad.api


class InstallFailed(Exception):
    pass


class DownloadFailed(Exception):
    pass


class UninstallFailed(Exception):
    pass


def retry(max_attempt):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            success = False
            current_attempt = 1
            last_exception = None

            while not success and current_attempt <= max_attempt:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    current_attempt += 1
                    last_exception = e

            if not success:
                raise last_exception

        return wrapper

    return decorator


@retry(max_attempt=3)
def _install_dataset(dataset_path: str, *, recursive: bool = False):
    full_path = os.path.join(os.getcwd(), dataset_path)
    datalad.api.install(path=full_path, recursive=recursive, on_failure="stop")


def install_dataset(dataset_path: str, *, recursive: bool = False) -> None:
    try:
        _install_dataset(dataset_path, recursive=recursive)
    except Exception as e:
        raise InstallFailed(f"Installation failed for dataset: {dataset_path}\n{e}")


@retry(max_attempt=3)
def _get_dataset(dataset_path: str, *, recursive: bool = False) -> None:
    full_path = os.path.join(os.getcwd(), dataset_path)
    datalad.api.get(path=full_path, recursive=recursive, on_failure="stop")


def get_dataset(dataset_path: str, *, recursive: bool = False) -> None:
    try:
        _get_dataset(dataset_path, recursive=recursive)
    except Exception as e:
        raise DownloadFailed(f"Download failed for dataset: {dataset_path}\n{e}")


@retry(max_attempt=3)
def _uninstall_dataset(dataset_path: str, *, recursive: bool = False):
    full_path = os.path.join(os.getcwd(), dataset_path)
    datalad.api.uninstall(path=full_path, recursive=recursive, on_failure="stop")


def uninstall_dataset(dataset_path: str, *, recursive: bool = False) -> None:
    try:
        _uninstall_dataset(dataset_path, recursive=recursive)
    except Exception as e:
        raise UninstallFailed(f"Installation failed for dataset: {dataset_path}\n{e}")
