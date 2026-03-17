"""Interactive formatting feature scaffolding."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from black.interactive.apply import HunkApplier
from black.interactive.engine import build_hunks
from black.interactive.interfaces import FormatHunk, HunkDecision
from black.interactive.io import TerminalPrompt, TerminalRenderer
from black.interactive.session import TerminalSession


def run_interactive_mode(
    *,
    src: Path,
    original_content: str,
    formatted_content: str,
    mode: str = "per-hunk",
) -> str:
    """Run interactive formatting mode for a file.

    Args:
        src: Path to the file being formatted.
        original_content: Original file content.
        formatted_content: Formatted file content.
        mode: Interactive mode - "per-hunk", "accept-all", or "reject-all".

    Returns:
        Modified content string (only accepted hunks applied).
    """
    original_lines = original_content.splitlines(keepends=True)
    formatted_lines = formatted_content.splitlines(keepends=True)

    # Build hunks
    hunks_map = build_hunks(
        file_path=src,
        original=original_lines,
        formatted=formatted_lines,
    )

    if not hunks_map:
        # No changes
        return original_content

    hunks: list[FormatHunk] = list(hunks_map.keys())

    # Handle different modes
    if mode == "accept-all":
        accepted = hunks
    elif mode == "reject-all":
        accepted = []
    else:
        # per-hunk mode: interactive prompt
        accepted = _interactive_prompt_loop(src, hunks)

    # Apply accepted hunks
    applier = HunkApplier()
    modified_lines = applier.apply(
        file_path=src,
        original=original_lines,
        accepted=accepted,
    )

    return "".join(modified_lines)


def _interactive_prompt_loop(
    src: Path,
    hunks: Sequence[FormatHunk],
) -> list[FormatHunk]:
    """Run interactive prompt loop for hunks.

    Returns list of accepted hunks.
    """
    prompt = TerminalPrompt()
    renderer = TerminalRenderer()
    session = TerminalSession(verbose=True)

    from black.interactive.interfaces import HunkBatch, HunkSource

    batch = HunkBatch(
        file_path=src,
        hunks=list(hunks),
        source=HunkSource.DIFF,
    )

    session.start(batch)

    accepted: list[FormatHunk] = []

    print(f"\n{'=' * 60}")
    print(f"File: {src}")
    print(f"Found {len(hunks)} formatting change(s)")
    print(f"{'=' * 60}")
    print("\nOptions: [a]ccept / [r]eject / [A]ccept all / [R]eject all / [q]uit")

    for i, hunk in enumerate(hunks, 1):
        print(f"\n{'-' * 60}")
        print(f"Hunk {i}/{len(hunks)}: {hunk.hunk_id}")
        print(f"{'-' * 60}")

        # Show the hunk
        for line in renderer.render(hunk):
            print(line)

        # Get decision
        while True:
            try:
                choice = input("\n[a]ccept / [r]eject / [A]ll accept / [R]eject all / [q]uit: ").strip()
                if choice in ("a", "A", "y", "yes"):
                    accepted.append(hunk)
                    session.record_decision(HunkDecision.ACCEPT)
                    if choice == "A":
                        # Accept all remaining
                        accepted.extend(hunks[i:])
                        for _ in range(i, len(hunks)):
                            session.record_decision(HunkDecision.ACCEPT)
                        print(f"Accepted all remaining {len(hunks) - i + 1} hunks.")
                        return accepted
                    break
                elif choice in ("r", "R", "n", "no"):
                    session.record_decision(HunkDecision.REJECT)
                    if choice == "R":
                        # Reject all remaining (just skip them)
                        print(f"Rejected all remaining {len(hunks) - i + 1} hunks.")
                        session.finish(batch)
                        return accepted
                    break
                elif choice in ("q", "quit", "exit"):
                    print("Quitting interactive mode.")
                    session.finish(batch)
                    return accepted
                else:
                    print("Invalid choice. Please enter a, r, A, R, or q.")
            except EOFError:
                print("\nEOF received, skipping remaining hunks.")
                session.finish(batch)
                return accepted

    session.finish(batch)
    return accepted
