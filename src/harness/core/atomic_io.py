"""Shared atomic file write utility.

Provides a single implementation of write-to-tmp + os.replace for all modules
that need crash-safe file writes (barriers, workflow-state, etc.).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text_atomic(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via tmp file + rename.

    Uses ``mkstemp`` in the target directory so the rename is guaranteed
    to be on the same filesystem (required for ``os.replace`` atomicity).
    Cleans up the temp file on any failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}.",
        suffix=".tmp",
    )
    closed = False
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        closed = True
        os.replace(tmp_path_str, str(path))
    except BaseException:
        if not closed:
            os.close(fd)
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise
