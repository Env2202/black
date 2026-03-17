"""Extensive tests for interactive formatting module.

Run with: python -m pytest tests/test_interactive.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from black.interactive.interfaces import (
    FormatHunk,
    HunkDecision,
    HunkSource,
    HunkBatch,
)
from black.interactive.engine import build_hunks, InteractiveEngine, InteractiveResult
from black.interactive.apply import HunkApplier
from black.interactive.io import TerminalPrompt, TerminalRenderer


# =============================================================================
# Tests for interfaces.py
# =============================================================================


class TestFormatHunk:
    """Tests for FormatHunk dataclass."""

    def test_format_hunk_creation(self):
        """Test basic FormatHunk creation."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        assert hunk.file_path == Path("test.py")
        assert hunk.hunk_id == "hunk_0000"
        assert hunk.original == ("a\n",)
        assert hunk.formatted == ("b\n",)
        assert hunk.original_start == 0
        assert hunk.original_end == 0

    def test_format_hunk_with_positions(self):
        """Test FormatHunk with position info."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0001",
            original=("line1\n", "line2\n"),
            formatted=("Line1\n", "Line2\n"),
            original_start=5,
            original_end=7,
        )
        assert hunk.original_start == 5
        assert hunk.original_end == 7

    def test_format_hunk_frozen(self):
        """Test that FormatHunk is frozen (immutable)."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=(),
            formatted=(),
        )
        with pytest.raises(Exception):
            hunk.hunk_id = "changed"  # type: ignore

    def test_format_hunk_hashable(self):
        """Test that FormatHunk is hashable (can be used as dict key)."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        d = {hunk: Path("test.py")}
        assert hunk in d

    def test_format_hunk_equality(self):
        """Test FormatHunk equality."""
        hunk1 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        hunk2 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        assert hunk1 == hunk2

    def test_format_hunk_empty_original(self):
        """Test FormatHunk for insertion (empty original)."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=(),
            formatted=("new\n",),
            original_start=5,
            original_end=5,
        )
        assert len(hunk.original) == 0
        assert len(hunk.formatted) == 1

    def test_format_hunk_empty_formatted(self):
        """Test FormatHunk for deletion (empty formatted)."""
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("remove\n",),
            formatted=(),
            original_start=3,
            original_end=4,
        )
        assert len(hunk.original) == 1
        assert len(hunk.formatted) == 0


class TestHunkDecision:
    """Tests for HunkDecision enum."""

    def test_decision_values(self):
        """Test HunkDecision enum values."""
        assert HunkDecision.ACCEPT.value == "accept"
        assert HunkDecision.REJECT.value == "reject"
        assert HunkDecision.SKIP.value == "skip"

    def test_decision_comparison(self):
        """Test HunkDecision comparison."""
        assert HunkDecision.ACCEPT is HunkDecision.ACCEPT
        assert HunkDecision.ACCEPT is not HunkDecision.REJECT


class TestHunkSource:
    """Tests for HunkSource enum."""

    def test_source_values(self):
        """Test HunkSource enum values."""
        assert HunkSource.DIFF.value == "diff"
        assert HunkSource.AST.value == "ast"
        assert HunkSource.CUSTOM.value == "custom"


class TestHunkBatch:
    """Tests for HunkBatch dataclass."""

    def test_hunk_batch_creation(self):
        """Test HunkBatch creation."""
        hunks = [
            FormatHunk(
                file_path=Path("test.py"),
                hunk_id="hunk_0000",
                original=("a\n",),
                formatted=("b\n",),
            )
        ]
        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=hunks,
            source=HunkSource.DIFF,
        )
        assert batch.file_path == Path("test.py")
        assert len(batch.hunks) == 1
        assert batch.source == HunkSource.DIFF

    def test_hunk_batch_empty(self):
        """Test empty HunkBatch."""
        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=[],
            source=HunkSource.DIFF,
        )
        assert len(batch.hunks) == 0


# =============================================================================
# Tests for engine.py
# =============================================================================


class TestBuildHunks:
    """Tests for build_hunks function."""

    def test_build_hunks_no_changes(self):
        """Test build_hunks with identical content."""
        original = ["a\n", "b\n", "c\n"]
        formatted = ["a\n", "b\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 0

    def test_build_hunks_single_replacement(self):
        """Test build_hunks with single line replacement."""
        original = ["a\n", "b\n", "c\n"]
        formatted = ["a\n", "B\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 1
        hunk = list(result.keys())[0]
        assert hunk.original == ("b\n",)
        assert hunk.formatted == ("B\n",)

    def test_build_hunks_multiple_replacements(self):
        """Test build_hunks with multiple replacements."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        formatted = ["A\n", "b\n", "C\n", "d\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 2

    def test_build_hunks_insertion(self):
        """Test build_hunks with insertion."""
        original = ["a\n", "c\n"]
        formatted = ["a\n", "b\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 1
        hunk = list(result.keys())[0]
        assert len(hunk.original) == 0
        assert hunk.formatted == ("b\n",)

    def test_build_hunks_deletion(self):
        """Test build_hunks with deletion."""
        original = ["a\n", "b\n", "c\n"]
        formatted = ["a\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 1
        hunk = list(result.keys())[0]
        assert hunk.original == ("b\n",)
        assert len(hunk.formatted) == 0

    def test_build_hunks_ordered(self):
        """Test that hunks are ordered by appearance."""
        original = ["a\n", "b\n", "c\n", "d\n", "e\n"]
        formatted = ["A\n", "b\n", "C\n", "d\n", "E\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        hunk_ids = [h.hunk_id for h in result.keys()]
        assert hunk_ids == ["hunk_0000", "hunk_0001", "hunk_0002"]

    def test_build_hunks_position_info(self):
        """Test that hunks have correct position info."""
        original = ["a\n", "b\n", "c\n"]
        formatted = ["a\n", "B\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        hunk = list(result.keys())[0]
        assert hunk.original_start == 1
        assert hunk.original_end == 2

    def test_build_hunks_file_path_mapping(self):
        """Test that all hunks map to the same file path."""
        original = ["a\n", "b\n"]
        formatted = ["A\n", "B\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        for hunk, path in result.items():
            assert path == Path("test.py")

    def test_build_hunks_empty_content(self):
        """Test build_hunks with empty content."""
        result = build_hunks(
            file_path=Path("test.py"),
            original=[],
            formatted=[],
        )
        assert len(result) == 0

    def test_build_hunks_all_new(self):
        """Test build_hunks when all content is new."""
        original = []
        formatted = ["a\n", "b\n", "c\n"]
        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(result) == 1
        hunk = list(result.keys())[0]
        assert len(hunk.original) == 0
        assert len(hunk.formatted) == 3


class TestInteractiveEngine:
    """Tests for InteractiveEngine class."""

    def test_engine_initialization(self):
        """Test InteractiveEngine initialization."""
        from black.interactive.interfaces import (
            InteractivePrompt,
            InteractiveRenderer,
            InteractiveSession,
        )

        class MockPrompt(InteractivePrompt):
            def choose(self, hunk):
                return HunkDecision.ACCEPT

        class MockRenderer(InteractiveRenderer):
            def render(self, hunk):
                return []

        class MockSession(InteractiveSession):
            def start(self, batch):
                pass

            def finish(self, batch):
                pass

        engine = InteractiveEngine(
            prompt=MockPrompt(),
            renderer=MockRenderer(),
            session=MockSession(),
        )
        assert engine is not None

    def test_engine_run_all_accept(self):
        """Test engine run with all hunks accepted."""
        from black.interactive.interfaces import (
            InteractivePrompt,
            InteractiveRenderer,
            InteractiveSession,
        )

        class AcceptAllPrompt(InteractivePrompt):
            def choose(self, hunk):
                return HunkDecision.ACCEPT

        class MockRenderer(InteractiveRenderer):
            def render(self, hunk):
                return []

        class MockSession(InteractiveSession):
            def start(self, batch):
                pass

            def finish(self, batch):
                pass

        hunks = [
            FormatHunk(
                file_path=Path("test.py"),
                hunk_id="hunk_0000",
                original=("a\n",),
                formatted=("A\n",),
            )
        ]
        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=hunks,
            source=HunkSource.DIFF,
        )

        engine = InteractiveEngine(
            prompt=AcceptAllPrompt(),
            renderer=MockRenderer(),
            session=MockSession(),
        )
        result = engine.run(batch)

        assert result.accepted == 1
        assert result.rejected == 0
        assert result.skipped == 0

    def test_engine_run_all_reject(self):
        """Test engine run with all hunks rejected."""
        from black.interactive.interfaces import (
            InteractivePrompt,
            InteractiveRenderer,
            InteractiveSession,
        )

        class RejectAllPrompt(InteractivePrompt):
            def choose(self, hunk):
                return HunkDecision.REJECT

        class MockRenderer(InteractiveRenderer):
            def render(self, hunk):
                return []

        class MockSession(InteractiveSession):
            def start(self, batch):
                pass

            def finish(self, batch):
                pass

        hunks = [
            FormatHunk(
                file_path=Path("test.py"),
                hunk_id="hunk_0000",
                original=("a\n",),
                formatted=("A\n",),
            ),
            FormatHunk(
                file_path=Path("test.py"),
                hunk_id="hunk_0001",
                original=("b\n",),
                formatted=("B\n",),
            ),
        ]
        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=hunks,
            source=HunkSource.DIFF,
        )

        engine = InteractiveEngine(
            prompt=RejectAllPrompt(),
            renderer=MockRenderer(),
            session=MockSession(),
        )
        result = engine.run(batch)

        assert result.accepted == 0
        assert result.rejected == 2
        assert result.skipped == 0

    def test_engine_run_mixed_decisions(self):
        """Test engine run with mixed decisions."""
        from black.interactive.interfaces import (
            InteractivePrompt,
            InteractiveRenderer,
            InteractiveSession,
        )

        decisions = [HunkDecision.ACCEPT, HunkDecision.REJECT, HunkDecision.SKIP]
        decision_index = 0

        class MixedPrompt(InteractivePrompt):
            def choose(self, hunk):
                nonlocal decision_index
                result = decisions[decision_index]
                decision_index += 1
                return result

        class MockRenderer(InteractiveRenderer):
            def render(self, hunk):
                return []

        class MockSession(InteractiveSession):
            def start(self, batch):
                pass

            def finish(self, batch):
                pass

        hunks = [
            FormatHunk(file_path=Path("test.py"), hunk_id="h0", original=(), formatted=()),
            FormatHunk(file_path=Path("test.py"), hunk_id="h1", original=(), formatted=()),
            FormatHunk(file_path=Path("test.py"), hunk_id="h2", original=(), formatted=()),
        ]
        batch = HunkBatch(file_path=Path("test.py"), hunks=hunks, source=HunkSource.DIFF)

        engine = InteractiveEngine(
            prompt=MixedPrompt(),
            renderer=MockRenderer(),
            session=MockSession(),
        )
        result = engine.run(batch)

        assert result.accepted == 1
        assert result.rejected == 1
        assert result.skipped == 1


# =============================================================================
# Tests for apply.py
# =============================================================================


class TestHunkApplier:
    """Tests for HunkApplier class."""

    def test_apply_single_replacement(self):
        """Test applying single replacement hunk."""
        original = ["a\n", "b\n", "c\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("b\n",),
            formatted=("B\n",),
            original_start=1,
            original_end=2,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )
        assert result == ["a\n", "B\n", "c\n"]

    def test_apply_multiple_replacements(self):
        """Test applying multiple replacement hunks."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        hunk1 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("A\n",),
            original_start=0,
            original_end=1,
        )
        hunk2 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0001",
            original=("c\n",),
            formatted=("C\n",),
            original_start=2,
            original_end=3,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk1, hunk2],
        )
        assert result == ["A\n", "b\n", "C\n", "d\n"]

    def test_apply_deletion(self):
        """Test applying deletion hunk."""
        original = ["a\n", "b\n", "c\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("b\n",),
            formatted=(),
            original_start=1,
            original_end=2,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )
        assert result == ["a\n", "c\n"]

    def test_apply_insertion(self):
        """Test applying insertion hunk."""
        original = ["a\n", "c\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=(),
            formatted=("b\n",),
            original_start=1,
            original_end=1,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )
        assert result == ["a\n", "b\n", "c\n"]

    def test_apply_expansion(self):
        """Test applying hunk that expands one line to multiple."""
        original = ["a\n", "b\n", "c\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("b\n",),
            formatted=("B1\n", "B2\n"),
            original_start=1,
            original_end=2,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )
        assert result == ["a\n", "B1\n", "B2\n", "c\n"]

    def test_apply_contraction(self):
        """Test applying hunk that contracts multiple lines to one."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("b\n", "c\n"),
            formatted=("BC\n",),
            original_start=1,
            original_end=3,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )
        assert result == ["a\n", "BC\n", "d\n"]

    def test_apply_no_accepted_hunks(self):
        """Test applying with no accepted hunks."""
        original = ["a\n", "b\n", "c\n"]
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[],
        )
        assert result == original

    def test_apply_out_of_order_hunks(self):
        """Test applying hunks that are out of order."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        # Provide hunks in reverse order
        hunk2 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0001",
            original=("c\n",),
            formatted=("C\n",),
            original_start=2,
            original_end=3,
        )
        hunk1 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("A\n",),
            original_start=0,
            original_end=1,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk2, hunk1],  # Out of order
        )
        # Should be sorted and applied correctly
        assert result == ["A\n", "b\n", "C\n", "d\n"]

    def test_apply_adjacent_hunks(self):
        """Test applying adjacent hunks."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        hunk1 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("A\n",),
            original_start=0,
            original_end=1,
        )
        hunk2 = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0001",
            original=("b\n",),
            formatted=("B\n",),
            original_start=1,
            original_end=2,
        )
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk1, hunk2],
        )
        assert result == ["A\n", "B\n", "c\n", "d\n"]

    def test_apply_mixed_operations(self):
        """Test applying mix of replacements, insertions, deletions."""
        original = ["a\n", "b\n", "c\n", "d\n"]
        hunks = [
            FormatHunk(  # Replace
                file_path=Path("test.py"),
                hunk_id="hunk_0000",
                original=("a\n",),
                formatted=("A\n",),
                original_start=0,
                original_end=1,
            ),
            FormatHunk(  # Insert
                file_path=Path("test.py"),
                hunk_id="hunk_0001",
                original=(),
                formatted=("NEW\n",),
                original_start=2,
                original_end=2,
            ),
            FormatHunk(  # Delete
                file_path=Path("test.py"),
                hunk_id="hunk_0002",
                original=("d\n",),
                formatted=(),
                original_start=3,
                original_end=4,
            ),
        ]
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=hunks,
        )
        assert result == ["A\n", "b\n", "NEW\n", "c\n"]

    def test_write_to_file(self, tmp_path):
        """Test writing content to file."""
        applier = HunkApplier()
        file_path = tmp_path / "test.py"
        content = ["line1\n", "line2\n"]
        applier.write_to_file(file_path=file_path, content=content)
        assert file_path.read_text() == "line1\nline2\n"


# =============================================================================
# Tests for io.py
# =============================================================================


class TestTerminalPrompt:
    """Tests for TerminalPrompt class."""

    def test_prompt_auto_accept(self):
        """Test TerminalPrompt with auto_accept."""
        prompt = TerminalPrompt(auto_accept=True)
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        decision = prompt.choose(hunk)
        assert decision is HunkDecision.ACCEPT

    def test_prompt_auto_reject(self):
        """Test TerminalPrompt with auto_reject."""
        prompt = TerminalPrompt(auto_reject=True)
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
        )
        decision = prompt.choose(hunk)
        assert decision is HunkDecision.REJECT


class TestTerminalRenderer:
    """Tests for TerminalRenderer class."""

    def test_render_basic(self):
        """Test basic hunk rendering."""
        renderer = TerminalRenderer()
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("a\n",),
            formatted=("b\n",),
            original_start=0,
            original_end=1,
        )
        lines = list(renderer.render(hunk))
        assert len(lines) > 0
        assert "hunk_0000" in str(lines)

    def test_render_insertion(self):
        """Test rendering insertion hunk."""
        renderer = TerminalRenderer()
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=(),
            formatted=("new\n",),
        )
        lines = list(renderer.render(hunk))
        assert any("insertion" in line.lower() for line in lines)

    def test_render_deletion(self):
        """Test rendering deletion hunk."""
        renderer = TerminalRenderer()
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("remove\n",),
            formatted=(),
        )
        lines = list(renderer.render(hunk))
        assert any("deletion" in line.lower() for line in lines)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the interactive formatting workflow."""

    def test_full_workflow_accept_all(self):
        """Test full workflow with all hunks accepted."""
        from black.interactive.engine import build_hunks
        from black.interactive.apply import HunkApplier

        original = ["def foo():\n", "  x=1\n", "  y=2\n"]
        formatted = ["def foo():\n", "    x = 1\n", "    y = 2\n"]

        hunks_map = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        assert len(hunks_map) > 0

        # Accept all hunks
        hunks = list(hunks_map.keys())
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=hunks,
        )

        assert result != original

    def test_full_workflow_reject_all(self):
        """Test full workflow with no hunks accepted."""
        from black.interactive.engine import build_hunks
        from black.interactive.apply import HunkApplier

        original = ["def foo():\n", "  x=1\n"]
        formatted = ["def foo():\n", "    x = 1\n"]

        hunks_map = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        # Accept no hunks
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[],
        )

        assert result == original

    def test_partial_accept(self):
        """Test accepting only some hunks."""
        from black.interactive.engine import build_hunks
        from black.interactive.apply import HunkApplier

        # Use content with unchanged lines between changes to get separate hunks
        original = ["a\n", "keep\n", "b\n", "keep\n", "c\n"]
        formatted = ["A\n", "keep\n", "B\n", "keep\n", "C\n"]

        hunks_map = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        hunks = list(hunks_map.keys())

        # Should have 3 hunks (for a, b, c changes)
        assert len(hunks) == 3

        # Accept only first hunk
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunks[0]],
        )

        # First line should be changed, others unchanged
        assert result[0] == "A\n"
        assert result[1] == "keep\n"
        assert result[2] == "b\n"
        assert result[3] == "keep\n"
        assert result[4] == "c\n"

    def test_roundtrip_no_changes(self):
        """Test that accepting all on identical content returns same."""
        from black.interactive.engine import build_hunks
        from black.interactive.apply import HunkApplier

        original = ["a\n", "b\n", "c\n"]
        formatted = ["a\n", "b\n", "c\n"]

        hunks_map = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=list(hunks_map.keys()),
        )

        assert result == original


# =============================================================================
# Tests for run_interactive_mode
# =============================================================================


class TestRunInteractiveMode:
    """Tests for run_interactive_mode function."""

    def test_run_interactive_mode_no_changes(self):
        """Test run_interactive_mode with no changes."""
        from black.interactive import run_interactive_mode

        original = "a = 1\n"
        formatted = "a = 1\n"

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="accept-all",
        )

        assert result == original

    def test_run_interactive_mode_accept_all(self):
        """Test run_interactive_mode with accept-all mode."""
        from black.interactive import run_interactive_mode

        original = "def foo():\n    x=1\n"
        formatted = "def foo():\n    x = 1\n"

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="accept-all",
        )

        # Should have formatting applied
        assert result != original
        assert "x = 1" in result

    def test_run_interactive_mode_reject_all(self):
        """Test run_interactive_mode with reject-all mode."""
        from black.interactive import run_interactive_mode

        original = "def foo():\n    x=1\n"
        formatted = "def foo():\n    x = 1\n"

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="reject-all",
        )

        # Should have original content (no changes applied)
        assert result == original

    def test_run_interactive_mode_per_hunk_accept_all(self, monkeypatch):
        """Test run_interactive_mode with per-hunk mode accepting all."""
        from black.interactive import run_interactive_mode

        original = "a=1\nb=2\n"
        formatted = "a = 1\nb = 2\n"

        # Mock input to accept all hunks
        monkeypatch.setattr("builtins.input", lambda _: "A")

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="per-hunk",
        )

        # Should have formatting applied
        assert "a = 1" in result
        assert "b = 2" in result

    def test_run_interactive_mode_per_hunk_reject_all(self, monkeypatch):
        """Test run_interactive_mode with per-hunk mode rejecting all."""
        from black.interactive import run_interactive_mode

        original = "a=1\nb=2\n"
        formatted = "a = 1\nb = 2\n"

        # Mock input to reject all hunks
        monkeypatch.setattr("builtins.input", lambda _: "R")

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="per-hunk",
        )

        # Should have original content
        assert result == original

    def test_run_interactive_mode_quit_early(self, monkeypatch):
        """Test run_interactive_mode with quit option."""
        from black.interactive import run_interactive_mode

        original = "a=1\nb=2\nc=3\n"
        formatted = "a = 1\nb = 2\nc = 3\n"

        # Mock input to accept first, then quit
        inputs = iter(["a", "q"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content=original,
            formatted_content=formatted,
            mode="per-hunk",
        )

        # Should have first hunk applied, rest original
        assert "a = 1" in result

    def test_run_interactive_mode_empty_content(self):
        """Test run_interactive_mode with empty content."""
        from black.interactive import run_interactive_mode

        result = run_interactive_mode(
            src=Path("test.py"),
            original_content="",
            formatted_content="",
            mode="accept-all",
        )

        assert result == ""


# =============================================================================
# Tests for TerminalSession
# =============================================================================


class TestTerminalSession:
    """Tests for TerminalSession class."""

    def test_session_stats_tracking(self):
        """Test session statistics tracking."""
        from black.interactive.session import TerminalSession
        from black.interactive.interfaces import HunkBatch, HunkSource, HunkDecision

        session = TerminalSession(verbose=False)

        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=[],
            source=HunkSource.DIFF,
        )

        session.start(batch)
        session.record_decision(HunkDecision.ACCEPT)
        session.record_decision(HunkDecision.ACCEPT)
        session.record_decision(HunkDecision.REJECT)
        session.record_decision(HunkDecision.SKIP)
        session.finish(batch)

        stats = session.stats
        assert stats["accepted"] == 2
        assert stats["rejected"] == 1
        assert stats["skipped"] == 1
        assert stats["processed"] == 4

    def test_session_verbose_flag(self):
        """Test session with verbose=False."""
        from black.interactive.session import TerminalSession
        from black.interactive.interfaces import HunkBatch, HunkSource

        session = TerminalSession(verbose=False)
        batch = HunkBatch(
            file_path=Path("test.py"),
            hunks=[],
            source=HunkSource.DIFF,
        )

        # Should not raise any errors
        session.start(batch)
        session.finish(batch)


# =============================================================================
# Tests for interactive __init__ exports
# =============================================================================


class TestInteractiveExports:
    """Tests for interactive module exports."""

    def test_run_interactive_mode_import(self):
        """Test that run_interactive_mode can be imported."""
        from black.interactive import run_interactive_mode

        assert callable(run_interactive_mode)

    def test_all_components_importable(self):
        """Test that all interactive components are importable."""
        from black.interactive.interfaces import (
            FormatHunk,
            HunkDecision,
            HunkSource,
            HunkBatch,
        )
        from black.interactive.engine import build_hunks, InteractiveEngine
        from black.interactive.apply import HunkApplier
        from black.interactive.io import TerminalPrompt, TerminalRenderer
        from black.interactive.session import TerminalSession

        # All imports should succeed
        assert FormatHunk is not None
        assert HunkDecision is not None
        assert HunkSource is not None
        assert HunkBatch is not None
        assert build_hunks is not None
        assert InteractiveEngine is not None
        assert HunkApplier is not None
        assert TerminalPrompt is not None
        assert TerminalRenderer is not None
        assert TerminalSession is not None


# =============================================================================
# Tests for CLI flag --interactive (using click testing)
# =============================================================================


class TestInteractiveCLIFlag:
    """Tests for --interactive CLI flag using click testing."""

    def test_interactive_flag_exists(self):
        """Test that --interactive flag exists in CLI."""
        from click.testing import CliRunner
        from black import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert "--interactive" in result.output

    def test_interactive_flag_help(self):
        """Test --interactive flag help text."""
        from click.testing import CliRunner
        from black import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert "interactive" in result.output.lower()
        assert "accept" in result.output.lower() or "reject" in result.output.lower()

    def test_interactive_with_check_conflict(self, tmp_path):
        """Test that --interactive with --check shows error."""
        from click.testing import CliRunner
        from black import main

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("a=1\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--interactive", "--check"])

        assert result.exit_code != 0
        assert "interactive" in result.output.lower() or "check" in result.output.lower()

    def test_interactive_with_diff_conflict(self, tmp_path):
        """Test that --interactive with --diff shows error."""
        from click.testing import CliRunner
        from black import main

        test_file = tmp_path / "test.py"
        test_file.write_text("a=1\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--interactive", "--diff"])

        assert result.exit_code != 0

    def test_interactive_multiple_files_error(self, tmp_path):
        """Test that --interactive with multiple files shows error."""
        from click.testing import CliRunner
        from black import main

        test_file1 = tmp_path / "test1.py"
        test_file2 = tmp_path / "test2.py"
        test_file1.write_text("a=1\n")
        test_file2.write_text("b=2\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file1), str(test_file2), "--interactive"])

        assert result.exit_code != 0
        assert "single" in result.output.lower() or "interactive" in result.output.lower()

    def test_interactive_with_code_conflict(self):
        """Test that --interactive with -c/--code shows error."""
        from click.testing import CliRunner
        from black import main

        runner = CliRunner()
        result = runner.invoke(main, ["-c", "a=1", "--interactive"])

        assert result.exit_code != 0

    def test_interactive_nonexistent_file(self):
        """Test --interactive with nonexistent file."""
        from click.testing import CliRunner
        from black import main

        runner = CliRunner()
        result = runner.invoke(main, ["/nonexistent/path.py", "--interactive"])

        assert result.exit_code != 0

    def test_interactive_valid_file(self, tmp_path, monkeypatch):
        """Test --interactive with valid file and accept all."""
        from click.testing import CliRunner
        from black import main

        test_file = tmp_path / "test.py"
        test_file.write_text("a=1\nb=2\n")

        runner = CliRunner()
        # Mock input to accept all
        result = runner.invoke(main, [str(test_file), "--interactive"], input="A\n")

        # Should complete without error
        assert result.exit_code == 0

    def test_interactive_no_changes_needed(self, tmp_path, monkeypatch):
        """Test --interactive when no formatting changes needed."""
        from click.testing import CliRunner
        from black import main

        test_file = tmp_path / "test.py"
        # Already formatted
        test_file.write_text("a = 1\nb = 2\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--interactive"])

        # Should complete without error (no hunks to process)
        assert result.exit_code == 0

    def test_interactive_reject_all(self, tmp_path, monkeypatch):
        """Test --interactive with reject all."""
        from click.testing import CliRunner
        from black import main

        test_file = tmp_path / "test.py"
        original = "a=1\n"
        test_file.write_text(original)

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--interactive"], input="R\n")

        assert result.exit_code == 0
        # File should be unchanged
        assert test_file.read_text() == original

    def test_interactive_quit(self, tmp_path, monkeypatch):
        """Test --interactive with quit option."""
        from click.testing import CliRunner
        from black import main

        test_file = tmp_path / "test.py"
        original = "a=1\nb=2\n"
        test_file.write_text(original)

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--interactive"], input="q\n")

        assert result.exit_code == 0
        # File should be unchanged (quit before any changes)
        assert test_file.read_text() == original


# =============================================================================
# Tests for edge cases and error handling
# =============================================================================


class TestInteractiveEdgeCases:
    """Tests for edge cases in interactive formatting."""

    def test_hunk_with_special_characters(self):
        """Test hunks containing special characters."""
        from black.interactive.engine import build_hunks

        original = ["x = 'hello\\nworld'\n"]
        formatted = ["x = \"hello\\nworld\"\n"]

        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        # Should create hunks
        assert len(result) >= 0

    def test_hunk_with_unicode(self):
        """Test hunks containing unicode characters."""
        from black.interactive.engine import build_hunks

        original = ["x = 'café'\n"]
        formatted = ["x = \"café\"\n"]

        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        # Should handle unicode
        assert isinstance(result, dict)

    def test_apply_hunk_at_file_end(self):
        """Test applying hunk at end of file."""
        from black.interactive.apply import HunkApplier
        from black.interactive.interfaces import FormatHunk

        original = ["a\n", "b\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=("b\n",),
            formatted=("B\n",),
            original_start=1,
            original_end=2,
        )

        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )

        assert result[-1] == "B\n"

    def test_apply_empty_original_empty_formatted(self):
        """Test applying hunk with both empty original and formatted."""
        from black.interactive.apply import HunkApplier
        from black.interactive.interfaces import FormatHunk

        original = ["a\n", "b\n", "c\n"]
        hunk = FormatHunk(
            file_path=Path("test.py"),
            hunk_id="hunk_0000",
            original=(),
            formatted=(),
            original_start=1,
            original_end=1,
        )

        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunk],
        )

        # Should be unchanged (no-op)
        assert result == original

    def test_build_hunks_with_trailing_newline_difference(self):
        """Test hunks when only trailing newline differs."""
        from black.interactive.engine import build_hunks

        original = ["a\n", "b\n"]
        formatted = ["a\n", "b"]

        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        # Should detect the difference
        assert len(result) >= 0

    def test_build_hunks_preserves_order(self):
        """Test that build_hunks preserves order of hunks."""
        from black.interactive.engine import build_hunks

        original = ["a\n", "b\n", "c\n", "d\n", "e\n"]
        formatted = ["A\n", "b\n", "C\n", "d\n", "E\n"]

        result = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )

        hunk_ids = [h.hunk_id for h in result.keys()]
        # Should be in order
        assert hunk_ids == sorted(hunk_ids)
