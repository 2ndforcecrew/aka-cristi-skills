"""Reject links/reparse points before reading or modifying installer-owned paths.

This protects against pre-existing redirection, not a malicious concurrent process
changing the filesystem between validation and use. No permissions are changed.
"""
import os
import stat
from pathlib import Path


def checked_path(path, error_type=ValueError):
    result = Path(os.path.abspath(os.path.expanduser(str(path))))
    for candidate in (result, *result.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise error_type('symlink or reparse-point path forbidden')
    return result
