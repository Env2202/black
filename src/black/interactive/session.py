"""Interactive session placeholders."""

from __future__ import annotations

from black.interactive.interfaces import HunkBatch


class TerminalSession:
    """Terminal session lifecycle placeholder."""

    def start(self, batch: HunkBatch) -> None:
        raise NotImplementedError

    def finish(self, batch: HunkBatch) -> None:
        raise NotImplementedError
