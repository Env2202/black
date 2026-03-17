"""Interactive input/output placeholders."""

from __future__ import annotations

from typing import Iterable

from black.interactive.interfaces import FormatHunk, HunkDecision


class TerminalPrompt:
    """Terminal prompt placeholder."""

    def choose(self, hunk: FormatHunk) -> HunkDecision:
        raise NotImplementedError


class TerminalRenderer:
    """Terminal renderer placeholder."""

    def render(self, hunk: FormatHunk) -> Iterable[str]:
        raise NotImplementedError
