"""Process-lifetime advisory lock; stale lock files are harmless after exit."""
from __future__ import annotations

import importlib
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tools.fs_safety import checked_path


class LockBusy(ValueError):
    pass


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path = checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(path.parent, 0o700)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NOINHERIT', 0)
    fd = os.open(path, flags, 0o600)
    acquired = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1:
            raise LockBusy('LOCK_UNSAFE')
        checked_path(path)
        if os.name == 'nt':
            library = importlib.import_module('msvcrt')
            if info.st_size == 0:
                os.write(fd, b'0')
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                library.locking(fd, library.LK_NBLCK, 1)
            except OSError:
                raise LockBusy('LOCK_BUSY') from None
        else:
            library = importlib.import_module('fcntl')
            try:
                library.flock(fd, library.LOCK_EX | library.LOCK_NB)
            except OSError:
                raise LockBusy('LOCK_BUSY') from None
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                os.lseek(fd, 0, os.SEEK_SET)
                library.locking(fd, library.LK_UNLCK, 1)
            else:
                library.flock(fd, library.LOCK_UN)
        os.close(fd)
