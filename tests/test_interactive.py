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

        original = ["a\n", "b\n", "c\n"]
        formatted = ["A\n", "B\n", "C\n"]

        hunks_map = build_hunks(
            file_path=Path("test.py"),
            original=original,
            formatted=formatted,
        )
        hunks = list(hunks_map.keys())

        # Accept only first hunk
        applier = HunkApplier()
        result = applier.apply(
            file_path=Path("test.py"),
            original=original,
            accepted=[hunks[0]],
        )

        # First line should be changed, others unchanged
        assert result[0] == "A\n"
        assert result[1] == "b\n"
        assert result[2] == "c\n"

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
