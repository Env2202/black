"""Interactive formatting orchestration placeholders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

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
) -> Iterable[FormatHunk]:
    """Create hunks from original and formatted content (placeholder)."""
    return []
