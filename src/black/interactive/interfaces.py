"""Interfaces and placeholder types for interactive formatting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence


class HunkDecision(Enum):
    """Decision result for a formatting hunk."""

    ACCEPT = "accept"
    REJECT = "reject"
    SKIP = "skip"


@dataclass(frozen=True)
class FormatHunk:
    """Represents a proposed formatting change chunk."""

    file_path: Path
    hunk_id: str
    original: tuple[str, ...]
    formatted: tuple[str, ...]


class HunkSource(Enum):
    """Source type for hunks (placeholder)."""

    DIFF = "diff"
    AST = "ast"
    CUSTOM = "custom"


@dataclass(frozen=True)
class HunkBatch:
    """Grouping of hunks for a single file."""

    file_path: Path
    hunks: Sequence[FormatHunk]
    source: HunkSource


class InteractivePrompt:
    """Prompt to request decisions (placeholder)."""

    def choose(self, hunk: FormatHunk) -> HunkDecision:
        raise NotImplementedError


class InteractiveRenderer:
    """Renderer for displaying hunks to the user (placeholder)."""

    def render(self, hunk: FormatHunk) -> Iterable[str]:
        raise NotImplementedError


class InteractiveSession:
    """Session lifecycle for interactive formatting (placeholder)."""

    def start(self, batch: HunkBatch) -> None:
        raise NotImplementedError

    def finish(self, batch: HunkBatch) -> None:
        raise NotImplementedError
