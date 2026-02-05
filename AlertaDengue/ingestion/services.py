from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterator

from django.conf import settings


def imported_files_root() -> Path:
    """
    Return the root directory where the worker can access imported files.

    Returns
    -------
    Path
        Imported files root.
    """
    root = getattr(settings, "IMPORTED_FILES_DIR", "/IMPORTED_FILES")
    return Path(root)


def sha256_file(path: Path, bufsize: int = 1024 * 1024) -> str:
    """
    Compute SHA256 of a file.

    Parameters
    ----------
    path : Path
        File path.
    bufsize : int
        Read buffer size.

    Returns
    -------
    str
        Hex digest.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def resolve_source_path(source_path: str) -> Path:
    """
    Resolve a run source_path to an absolute path in the worker container.

    Parameters
    ----------
    source_path : str
        Relative path stored in ingestion.run.source_path.

    Returns
    -------
    Path
        Absolute path within imported_files_root().
    """
    root = imported_files_root()
    p = Path(source_path)
    if p.is_absolute():
        return p
    return root / p
