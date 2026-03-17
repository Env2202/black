"""Applying accepted hunks to files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from black.interactive.interfaces import FormatHunk


class HunkApplier:
    """Apply accepted hunks to file content.

    Only hunks that are explicitly accepted will be written back to the file.
    Rejected and skipped hunks will retain their original content.
    """

    def apply(
        self,
        *,
        file_path: Path,
        original: Sequence[str],
        accepted: Iterable[FormatHunk],
    ) -> Sequence[str]:
        """Apply accepted hunks to original content and return modified content.

        Args:
            file_path: Path to the original file (used for logging/validation).
            original: Original file content as a sequence of lines.
            accepted: Iterable of FormatHunk objects that were accepted by the user.

        Returns:
            Modified content with only accepted hunks applied.
        """
        # Convert to list for mutable operations
        result: list[str] = list(original)

        # Convert accepted hunks to list
        accepted_hunks = list(accepted)

        # Sort hunks by their original position to apply in order
        # Use original_start from FormatHunk for reliable positioning
        hunks_with_pos: list[tuple[FormatHunk, int]] = [
            (hunk, hunk.original_start) for hunk in accepted_hunks
        ]
        hunks_with_pos.sort(key=lambda x: x[1])

        # Apply hunks in order, tracking offset
        offset = 0
        for hunk, orig_pos in hunks_with_pos:
            # Adjust position for previous changes
            pos = orig_pos + offset

            orig_lines = list(hunk.original)
            fmt_lines = list(hunk.formatted)

            old_len = len(orig_lines)
            new_len = len(fmt_lines)

            if old_len == 0:
                # Pure insertion: insert at position
                # Ensure position is within bounds
                pos = min(pos, len(result))
                result[pos:pos] = fmt_lines
            else:
                # Replacement or deletion
                # Ensure position is within bounds
                pos = min(pos, len(result))
                end_pos = min(pos + old_len, len(result))
                result[pos:end_pos] = fmt_lines

            # Update offset
            offset += new_len - old_len

        return result

    def write_to_file(
        self,
        *,
        file_path: Path,
        content: Sequence[str],
    ) -> None:
        """Write content back to the original file.

        Args:
            file_path: Path to write to.
            content: Content to write.
        """
        file_path.write_text("".join(content))
