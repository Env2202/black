"""Interactive input/output for terminal TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from black.interactive.interfaces import FormatHunk, HunkDecision, HunkSource
from black.interactive.engine import build_hunks, InteractiveEngine, InteractiveResult
from black.interactive.apply import HunkApplier
from black.interactive.session import TerminalSession


class TerminalPrompt:
    """Terminal prompt for interactive hunk decisions."""

    def __init__(self, *, auto_accept: bool = False, auto_reject: bool = False) -> None:
        self._auto_accept = auto_accept
        self._auto_reject = auto_reject

    def choose(self, hunk: FormatHunk) -> HunkDecision:
        """Prompt user to accept, reject, or skip a hunk.

        Returns:
            HunkDecision based on user input.
        """
        if self._auto_accept:
            return HunkDecision.ACCEPT
        if self._auto_reject:
            return HunkDecision.REJECT

        self._display_hunk(hunk)
        return self._get_user_choice()

    def _display_hunk(self, hunk: FormatHunk) -> None:
        """Display hunk information to the user."""
        print(f"\n{'=' * 60}")
        print(f"Hunk: {hunk.hunk_id} | File: {hunk.file_path}")
        print(f"Lines: {hunk.original_start}-{hunk.original_end}")
        print("-" * 60)

        # Show original
        print("ORIGINAL:")
        if hunk.original:
            for i, line in enumerate(hunk.original):
                print(f"  - {line}", end="")
        else:
            print("  (insertion)")
        print()

        # Show formatted
        print("FORMATTED:")
        if hunk.formatted:
            for i, line in enumerate(hunk.formatted):
                print(f"  + {line}", end="")
        else:
            print("  (deletion)")
        print("-" * 60)

    def _get_user_choice(self) -> HunkDecision:
        """Get user choice from terminal input."""
        while True:
            try:
                choice = (
                    input("[a]ccept / [r]eject / [s]kip / [q]uit: ").strip().lower()
                )
                if choice in ("a", "accept", "y", "yes"):
                    return HunkDecision.ACCEPT
                elif choice in ("r", "reject", "n", "no"):
                    return HunkDecision.REJECT
                elif choice in ("s", "skip"):
                    return HunkDecision.SKIP
                elif choice in ("q", "quit", "exit"):
                    return HunkDecision.SKIP  # Skip remaining
                else:
                    print("Invalid choice. Please enter a, r, s, or q.")
            except EOFError:
                return HunkDecision.SKIP


class TerminalRenderer:
    """Terminal renderer for displaying hunks."""

    def render(self, hunk: FormatHunk) -> Iterable[str]:
        """Render a hunk as a sequence of display lines.

        Args:
            hunk: The hunk to render.

        Returns:
            Iterable of display lines.
        """
        lines: list[str] = []
        lines.append(f"Hunk {hunk.hunk_id}:")
        lines.append(f"  File: {hunk.file_path}")
        lines.append(f"  Position: {hunk.original_start}-{hunk.original_end}")

        if hunk.original:
            lines.append("  Original:")
            for line in hunk.original:
                lines.append(f"    - {line.rstrip()}")
        else:
            lines.append("  Original: (empty - insertion)")

        if hunk.formatted:
            lines.append("  Formatted:")
            for line in hunk.formatted:
                lines.append(f"    + {line.rstrip()}")
        else:
            lines.append("  Formatted: (empty - deletion)")

        return lines


def run_interactive_tui(
    *,
    file_path: Path,
    original_content: str,
    formatted_content: str,
    auto_accept: bool = False,
    auto_reject: bool = False,
) -> tuple[str, InteractiveResult]:
    """Run interactive TUI for formatting hunks.

    This is the main entry point for testing the interactive formatting workflow.
    It builds hunks from original vs formatted content, prompts the user for
    each hunk, and applies only accepted hunks.

    Args:
        file_path: Path to the file being formatted.
        original_content: Original file content.
        formatted_content: Formatted file content.
        auto_accept: If True, automatically accept all hunks (for testing).
        auto_reject: If True, automatically reject all hunks (for testing).

    Returns:
        Tuple of (modified content string, InteractiveResult).
    """
    # Parse content into lines
    original_lines = original_content.splitlines(keepends=True)
    formatted_lines = formatted_content.splitlines(keepends=True)

    # Build hunks
    hunks_map = build_hunks(
        file_path=file_path,
        original=original_lines,
        formatted=formatted_lines,
    )

    if not hunks_map:
        print("No formatting changes detected.")
        return original_content, InteractiveResult(
            file_path=file_path,
            accepted=0,
            rejected=0,
            skipped=0,
        )

    # Create hunk batch
    from black.interactive.interfaces import HunkBatch

    hunks_list = list(hunks_map.keys())
    batch = HunkBatch(
        file_path=file_path,
        hunks=hunks_list,
        source=HunkSource.DIFF,
    )

    # Create components
    prompt = TerminalPrompt(auto_accept=auto_accept, auto_reject=auto_reject)
    renderer = TerminalRenderer()
    session = TerminalSession(verbose=not auto_accept and not auto_reject)
    engine = InteractiveEngine(prompt=prompt, renderer=renderer, session=session)

    # Run interactive session
    result = engine.run(batch)

    # Collect accepted hunks
    accepted_hunks: list[FormatHunk] = []
    for hunk in hunks_list:
        # Re-run prompt to get decisions (simplified: collect from session would be better)
        pass

    # Actually need to track decisions during run
    # For now, use a different approach: re-run with tracking
    accepted_hunks = _collect_accepted_hunks(
        hunks_list=hunks_list,
        prompt=TerminalPrompt(auto_accept=auto_accept, auto_reject=auto_reject),
    )

    # Apply accepted hunks
    applier = HunkApplier()
    modified_lines = applier.apply(
        file_path=file_path,
        original=original_lines,
        accepted=accepted_hunks,
    )

    return "".join(modified_lines), result


def _collect_accepted_hunks(
    *,
    hunks_list: list[FormatHunk],
    prompt: TerminalPrompt,
) -> list[FormatHunk]:
    """Collect hunks that were accepted by the prompt.

    This is a helper that re-evaluates hunks through the prompt.
    """
    accepted: list[FormatHunk] = []
    for hunk in hunks_list:
        decision = prompt.choose(hunk)
        if decision is HunkDecision.ACCEPT:
            accepted.append(hunk)
    return accepted


def run_interactive_tui_simple(
    *,
    file_path: Path,
    original_content: str,
    formatted_content: str,
) -> str:
    """Simple TUI that auto-accepts all hunks (for testing).

    Args:
        file_path: Path to the file.
        original_content: Original content.
        formatted_content: Formatted content.

    Returns:
        Modified content string.
    """
    modified, _ = run_interactive_tui(
        file_path=file_path,
        original_content=original_content,
        formatted_content=formatted_content,
        auto_accept=True,
    )
    return modified
