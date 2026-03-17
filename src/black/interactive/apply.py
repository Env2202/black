"""Applying accepted hunks to files (placeholder)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from black.interactive.interfaces import FormatHunk


class HunkApplier:
    """Apply accepted hunks to file content (placeholder)."""

    def apply(
        self,
        *,
        file_path: Path,
        original: Sequence[str],
        accepted: Iterable[FormatHunk],
    ) -> Sequence[str]:
        raise NotImplementedError
