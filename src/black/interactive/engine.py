"""Interactive formatting orchestration placeholders."""

from __future__ import annotations

import difflib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from black.interactive.interfaces import (
    FormatHunk,
    HunkBatch,
    HunkDecision,
    InteractivePrompt,
    InteractiveRenderer,
    InteractiveSession,
)


@dataclass(frozen=True)
class InteractiveResult:
    """Result summary for an interactive run (placeholder)."""

    file_path: Path
    accepted: int
    rejected: int
    skipped: int


class InteractiveEngine:
    """Coordinates interactive formatting decisions (placeholder)."""

    def __init__(
        self,
        *,
        prompt: InteractivePrompt,
        renderer: InteractiveRenderer,
        session: InteractiveSession,
    ) -> None:
        self._prompt = prompt
        self._renderer = renderer
        self._session = session

    def run(self, batch: HunkBatch) -> InteractiveResult:
        self._session.start(batch)
        accepted = 0
        rejected = 0
        skipped = 0
        for hunk in batch.hunks:
            decision = self._prompt.choose(hunk)
            if decision is HunkDecision.ACCEPT:
                accepted += 1
            elif decision is HunkDecision.REJECT:
                rejected += 1
            else:
                skipped += 1
        self._session.finish(batch)
        return InteractiveResult(
            file_path=batch.file_path,
            accepted=accepted,
            rejected=rejected,
            skipped=skipped,
        )


def build_hunks(
    *,
    file_path: Path,
    original: Sequence[str],
    formatted: Sequence[str],
) -> Mapping[FormatHunk, Path]:
    """Create hunks from original and formatted content.

    Compares original and formatted line sequences and returns an ordered map
    where each FormatHunk is mapped to its original file path. Hunks are ordered
    by their appearance in the file.

    Args:
        file_path: Path to the original file.
        original: Original content as a sequence of lines.
        formatted: Formatted content as a sequence of lines.

    Returns:
        An OrderedDict mapping each FormatHunk to its file_path.
    """
    if original == formatted:
        return OrderedDict()

    # Use SequenceMatcher to find matching blocks
    matcher = difflib.SequenceMatcher(None, list(original), list(formatted))

    hunks_map: OrderedDict[FormatHunk, Path] = OrderedDict()
    hunk_index = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        # Extract the original and formatted lines for this hunk
        orig_lines = tuple(original[i1:i2])
        fmt_lines = tuple(formatted[j1:j2])

        # Create a unique hunk_id based on position
        hunk_id = f"hunk_{hunk_index:04d}"

        # Create the FormatHunk with position info
        hunk = FormatHunk(
            file_path=file_path,
            hunk_id=hunk_id,
            original=orig_lines,
            formatted=fmt_lines,
            original_start=i1,
            original_end=i2,
        )

        # Map hunk to file_path in order
        hunks_map[hunk] = file_path
        hunk_index += 1

    return hunks_map
