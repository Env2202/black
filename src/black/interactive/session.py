"""Interactive session lifecycle management."""

from __future__ import annotations

from black.interactive.interfaces import HunkBatch


class TerminalSession:
    """Terminal session lifecycle for interactive formatting."""

    def __init__(self, *, verbose: bool = True) -> None:
        self._verbose = verbose
        self._hunks_processed = 0
        self._hunks_accepted = 0
        self._hunks_rejected = 0
        self._hunks_skipped = 0

    def start(self, batch: HunkBatch) -> None:
        """Start a new interactive session for a batch of hunks.

        Args:
            batch: The batch of hunks to process.
        """
        self._hunks_processed = 0
        self._hunks_accepted = 0
        self._hunks_rejected = 0
        self._hunks_skipped = 0

        if self._verbose:
            print(f"\n{'#' * 60}")
            print(f"Interactive Formatting Session")
            print(f"{'#' * 60}")
            print(f"File: {batch.file_path}")
            print(f"Source: {batch.source.value}")
            print(f"Total hunks: {len(batch.hunks)}")
            print(f"{'#' * 60}")

    def finish(self, batch: HunkBatch) -> None:
        """Finish the interactive session.

        Args:
            batch: The batch that was processed.
        """
        if self._verbose:
            print(f"\n{'#' * 60}")
            print("Session Summary")
            print(f"{'#' * 60}")
            print(f"File: {batch.file_path}")
            print(f"Total hunks: {len(batch.hunks)}")
            print(f"Accepted: {self._hunks_accepted}")
            print(f"Rejected: {self._hunks_rejected}")
            print(f"Skipped: {self._hunks_skipped}")
            print(f"{'#' * 60}")

    def record_decision(self, decision: "HunkDecision") -> None:
        """Record a decision for statistics.

        Args:
            decision: The decision that was made.
        """
        from black.interactive.interfaces import HunkDecision

        self._hunks_processed += 1
        if decision is HunkDecision.ACCEPT:
            self._hunks_accepted += 1
        elif decision is HunkDecision.REJECT:
            self._hunks_rejected += 1
        else:
            self._hunks_skipped += 1

    @property
    def stats(self) -> dict[str, int]:
        """Get session statistics.

        Returns:
            Dictionary with accepted, rejected, skipped counts.
        """
        return {
            "processed": self._hunks_processed,
            "accepted": self._hunks_accepted,
            "rejected": self._hunks_rejected,
            "skipped": self._hunks_skipped,
        }
