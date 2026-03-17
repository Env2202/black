# Feature Plan — Interactive hunk-based mode (`black --interactive`)

## Summary

Implement `black --interactive` that shows changes **hunk-by-hunk** and prompts the user to accept/reject each hunk. Only accepted hunks are written back to the original file(s).

This plan is written to be **LLM-executable**: it is phased, names concrete files, defines constraints, and includes acceptance criteria for each phase.

Interactive hunk review is valuable when teams want Black’s consistency but still need human control in sensitive areas (large diffs, legacy codebases, or changes near semantics-adjacent constructs like string formatting and comments): it lets you take the “safe” hunks immediately while deferring contentious ones, reducing review churn and minimizing surprise in large PRs. Technically, it’s moderately challenging because Black’s output is global but the UI decision is local: you must generate stable hunks, map those hunks back onto original/formatted line slices, and apply partial patches deterministically without corrupting files (encoding/newlines) or producing confusing prompts, all while keeping behavior reproducible and testable across platforms.

## Goals

- Add `black --interactive` to review formatting changes **hunk-by-hunk**.
- For each hunk, prompt user to **accept** or **reject**.
- Write back **only accepted** hunks to the original files.
- Keep existing `--diff` / `--check` behavior unchanged.

## Hard constraints (v1)

- `--interactive` is **mutually exclusive** with `--diff` and `--check`.
- `--interactive` **writes to files** (not stdout-only).
- v1 supports:
  - **Only path inputs** (no stdin `-`, no `--stdin-filename`, no `-c/--code`).
  - **Only `.py` and `.pyi`** (no interactive `.ipynb`).
  - **Sequential execution** (no multiprocessing; no interleaved prompts).
  - (Recommended) **No `--line-ranges`** in interactive mode for v1.

## Existing code to reuse

- CLI entrypoint and formatting pipeline: `[src/black/__init__.py](src/black/__init__.py)` (`main()`, `reformat_one()`, `format_file_in_place()`, `format_file_contents()`).
- Unified diff helper: `[src/black/output.py](src/black/output.py)` (`diff()` and `color_diff()` exist; interactive mode can render hunks separately).

## Approach overview

- Compute `dst_contents` using the existing formatter (as normal Black does).
- Use `difflib.SequenceMatcher(...).get_grouped_opcodes(n=context)` to group changes into hunks.
- For each hunk, show a unified-diff fragment and prompt the user.
- Reconstruct the final output by splicing either:
  - original lines for rejected hunks, or
  - formatted lines for accepted hunks.
- Write back only if the reconstructed output differs from the original input.

## Phase 0 — Pre-flight & pure core (no CLI wiring yet)

**Goal**: Establish a small, pure (no IO) core for computing hunks and applying hunk decisions.

**Files**:
- Create `[src/black/interactive.py](src/black/interactive.py)`.

**Work items**:
- Define `@dataclass Hunk` with fields sufficient to:
  - locate the changed region in original (`a_*`) and formatted (`b_*`) text
  - hold the grouped opcodes for rendering
- Implement pure functions with stable signatures:
  - `compute_hunks(a_text: str, b_text: str, *, context_lines: int = 5) -> list[Hunk]`
  - `apply_hunk_decisions(a_text: str, b_text: str, hunks: Sequence[Hunk], decisions: Sequence[bool]) -> str`

**Acceptance criteria**:
- `src/black/interactive.py` exists and is importable.
- `compute_hunks()` returns hunks in **monotonic order** with **non-overlapping** original ranges (`a_start..a_end`).
- `apply_hunk_decisions()` properties:
  - all `False` decisions → output equals `a_text`
  - all `True` decisions → output equals `b_text`
  - mixed decisions → deterministic output

**Implementation notes**:
- Use `difflib.SequenceMatcher(a_lines, b_lines).get_grouped_opcodes(n=context_lines)`.
- Construct output by walking hunks in order:
  - unchanged prefix from `a_lines`
  - splice from `a_lines` or `b_lines` based on decision
  - unchanged suffix from `a_lines`

## Phase 1 — Rendering and interactive loop (IO, still not wired into `black main`)

**Goal**: Build a minimal “TUI-like” prompt loop that can be driven via Click testing.

**Files**:
- Extend `[src/black/interactive.py](src/black/interactive.py)`.

**Work items**:
- Implement hunk rendering:
  - `render_hunk(hunk: Hunk, a_text: str, b_text: str, *, a_name: str, b_name: str) -> str`
  - Render a **unified diff fragment** per hunk.
  - Do **not** include full-file `---/+++` headers in the fragment (keep it compact).
- Implement prompt loop:
  - normalize inputs: `y`, `n`, `a`, `d`, `q`, `?`
  - `?` shows help and re-prompts for the same hunk
  - `q` aborts the session immediately
  - `a` accepts current and all remaining hunks in the file
  - `d` rejects current and all remaining hunks in the file

**Acceptance criteria**:
- Rendering output includes:
  - an `@@ -<a_range> +<b_range> @@` line
  - context lines prefixed with space
  - deletion lines prefixed with `-`
  - addition lines prefixed with `+`
- Prompt behavior matches key meanings exactly (y/n/a/d/q/?).
- Interactive loop uses Click I/O such that `click.testing.CliRunner(..., input=...)` can drive decisions.

## Phase 2 — CLI flag + pipeline wiring + write-back

**Goal**: Add `--interactive` flag and wire interactive decisions into formatting, with correct write-back semantics.

**Files**:
- Update `[src/black/__init__.py](src/black/__init__.py)`.

**Work items**:
- Add `--interactive` Click option to `main()`.
- Add validations in `main()` (clear error messages):
  - `--interactive` with `--diff` → error
  - `--interactive` with `--check` → error
  - `--interactive` with `-c/--code` → error
  - `--interactive` with stdin source `-` or `--stdin-filename` → error
  - `--interactive` with `.ipynb` (or `--ipynb`) → error
  - (Recommended for v1) `--interactive` with `--line-ranges` → error
- Implement interactive formatting function (location flexible, but must be called from `reformat_one()` when interactive is enabled):
  - read/decode like `format_file_in_place()`
  - compute `dst_contents` via `format_file_contents()`
  - if unchanged: return `False`
  - compute hunks between `src_contents` and `dst_contents`
  - run review loop to collect decisions
  - compute `patched_contents` with `apply_hunk_decisions()`
  - if patched differs: write back, preserving encoding/newline conventions
- Ensure interactive runs **sequentially** even if multiple files are supplied.

**Acceptance criteria**:
- `black --interactive path/to/file.py`:
  - shows hunks + prompts
  - reject all → file unchanged
  - accept some → file partially updated deterministically
  - accept all → file equals normal fully formatted output
- Invalid combinations fail fast with clear errors:
  - `--interactive --diff`, `--interactive --check`, `--interactive -c`, `--interactive -`
- Existing `--diff` output remains unchanged.

## Phase 3 — Tests

**Goal**: Add deterministic tests to prevent regressions and lock down UI/behavior contracts.

**Files**:
- Add `tests/test_interactive.py`.

**Work items**:
- Use `click.testing.CliRunner` and temporary files to validate real write-back.
- Test cases:
  - `accept_single_hunk`: input `y\n` → file fully formatted
  - `reject_single_hunk`: input `n\n` → file unchanged
  - `multi_hunk_mixed`: input `y\nn\n` → file matches expected partial application
  - `accept_all_shortcut`: input `a\n` → file fully formatted
  - `reject_all_shortcut`: input `d\n` → file unchanged
  - `help_reprompt`: input `?\ny\n` → help printed, then accepted
  - `flag_validation`: invalid combos error

**Acceptance criteria**:
- `python -m pytest` passes.
- Tests are deterministic across platforms (Windows/macOS/Linux).
- No reliance on terminal-specific behavior (no curses).

## Phase 4 — Documentation

**Goal**: Document usage and key bindings so the feature is discoverable.

**Files**:
- Update a doc under `docs/usage_and_configuration/` (choose the most appropriate existing page, or add a small new page).
- Ensure CLI help text is accurate.

**Work items**:
- Document:
  - what interactive mode does
  - the prompt keys (`y/n/a/d/q/?`)
  - v1 limitations (no stdin, no `-c`, no `.ipynb`, mutually exclusive with `--diff/--check`)

**Acceptance criteria**:
- Docs render cleanly and match implemented behavior.
- CLI help mentions key limitations and expected interaction pattern.

## Post-v1 follow-ups (explicitly out of scope)

- Interactive `.ipynb` review (cell-level hunks).
- Allow interactive + `--check` (exit-code-only semantics).
- Allow stdin / `-c` interactive with stdout patch output.
- Add paging/colors (still non-curses) and/or a richer UI.

