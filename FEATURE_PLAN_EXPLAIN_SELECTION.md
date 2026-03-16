# Feature Plan (Path 1): `black --explain` → rule analysis + simulation subsystem

## 🎯 Goal

Upgrade `black --explain` from “print a reason string” into a **rule analysis + simulation subsystem** that can:

- explain *what rule(s) applied* and *why* (with precedence/short-circuit semantics)
- simulate “what-if” changes (e.g., toggle `.gitignore`, adjust `--exclude`, test a new pattern) **without formatting**
- support **stable, machine-readable output** for tooling (JSON with reason codes + rule provenance)

This removes the need for users to mentally reconstruct the interaction between:

- explicit CLI arguments (files/dirs/stdin)
- `.gitignore` matching (per-directory)
- `--exclude` / `--extend-exclude`
- `--force-exclude`
- `--include`
- special cases (`.ipynb` dependency gating, symlink resolution outside root, unreadable paths)

This feature is intentionally scoped to be a **deep, multi-layer change** (CLI + rule-modeling + discovery + reporting + performance + tests + docs), suitable for ~10 iterative LLM turns to implement cleanly.

## 👥 Primary Users

- Developers onboarding to a repo who can’t tell why Black “skips” files.
- CI maintainers troubleshooting “Black didn’t format X” or “Black is formatting generated code”.
- Tool integrators invoking Black on changed files with `--force-exclude` and needing deterministic explanations.

## ✅ Non-goals (to prevent scope creep)

- A fully interactive UI.
- Changing default include/exclude behavior.
- Producing a complete trace for every low-level FS operation (keep output readable).
- Parsing and explaining exact `.gitignore` line-level matches in v1 (we’ll attribute to the `.gitignore` *file* and the match outcome first).

## 🧩 Proposed UX

### New CLI flags

- `--explain`: Enable explain output for path selection decisions (no formatting changes).
- `--explain-format {text,json}`: Default `text`.
- `--explain-simulate <SPEC>`: Run “what-if” simulations against the same discovered candidate set. Examples:
  - `--explain-simulate "no-gitignore"`
  - `--explain-simulate "exclude+=/generated/"`
  - `--explain-simulate "force-exclude+=/migrations/"`
  - `--explain-simulate "include=/\\.pyi?$/"` (override)
- `--explain-show {winner,trace}`:
  - `winner` (default): only the rule(s) that determined the final decision
  - `trace`: include a bounded, structured trace of rule evaluation steps
- `--explain-limit N`: cap printed decisions (default bounded, see Phase 6)

### Output shape (text)

For each input *argument* and for each discovered candidate (when scanning directories), emit one line per scenario:

- `BASE INCLUDED  path/to/file.py  (winner: include_regex_match; provenance: --include default)`
- `BASE IGNORED   path/to/file.py  (winner: gitignore_match; provenance: <dir>/.gitignore)`
- `SIM1 INCLUDED  path/to/file.py  (winner: include_regex_match; provenance: --include default; delta: was IGNORED by gitignore_match)`

When `--explain-show trace` is enabled, append a compact trace column (bounded):

- `trace: include✓ → force-exclude✗ → extend-exclude✗ → exclude✗ → gitignore✓ (stop)`

Always end with a summary:
- totals by decision type (base + per simulation)
- top winners (reason codes)
- truncation notice when applicable

## 🏗️ Architecture Notes (where this fits)

This touches the “Readers/Writers” + “Reporting” layers described in `OVERVIEW.md`:

- File discovery: `src/black/files.py` (`gen_python_files`, `.gitignore` checks, exclude checks)
- Source computation: `src/black/__init__.py:get_sources`
- Reporting: `src/black/report.py` + `src/black/output.py`

The central design question: **How do we represent “rules” so we can both explain and simulate outcomes without duplicating selection logic?**

Recommendation:

- Introduce an explicit **Path Selection Ruleset** model (pure logic, minimal IO) that can:
  - evaluate a normalized path against ordered rules with short-circuit semantics
  - emit a **winner** + optional bounded evaluation trace
  - be re-instantiated with modified rule parameters for simulation
- Keep file system walking in `files.py`, but delegate “should include/ignore + why” to the ruleset evaluator.
- Add an “explain channel” to `Report` (or parallel collector) that stores structured events:
  - scenario id (`BASE`, `SIM1`, …)
  - decision (included / ignored / skipped / invalid)
  - winner reason code
  - provenance (origin of the winning rule: CLI/config/default/gitignore-file)
  - optional trace (bounded list of evaluation steps)

## 🧠 Why this is non-trivial

This becomes a non-trivial task once we require **analysis + simulation**, not just extra logging:

- **A new internal abstraction boundary**: Today, path selection is “smeared” across `get_sources()` and `gen_python_files()` with early returns. Simulation requires extracting this into a reusable evaluator that is *pure* (no filesystem) yet still faithful to current semantics.
- **Precedence and short-circuit correctness**: The effective behavior depends on order (e.g., `.gitignore` vs `--exclude` vs `--force-exclude`, explicit args vs recursive discovery, directories vs files). A ruleset must preserve subtle order-dependent behavior, including directory pruning and how patterns are normalized (`/`-prefixed, trailing `/` for dirs).
- **Multi-scenario evaluation**: Simulation means running the evaluator multiple times per path with mutated rule parameters while keeping discovery constant. That requires:
  - stable candidate sets
  - explicit scenario ids
  - diffing base vs simulated winners (delta reporting)
- **Output stability + machine interface**: A useful subsystem needs deterministic ordering and a structured schema (especially for CI/editor integrations). This pushes the change beyond “trivial CLI flag” into API design and compatibility concerns.
- **Performance constraints**: Black is widely used on large repos. The subsystem must be near-zero overhead when off, and bounded/efficient when on (limits, truncation summaries, avoiding expensive per-path allocations).
- **Test matrix complexity**: The same inputs must be validated across platforms, path separators, nested `.gitignore` layering, and regex behavior. Add simulations and the test surface multiplies.

## 📦 Phased Implementation Plan (10-turn sized)

### Phase 0 — Ruleset spec + reason/provenance contracts (no behavior change)

**Deliverables**

- Define a stable set of **reason codes** + **provenance types**:
  - `gitignore_match`
  - `exclude_regex_match`
  - `extend_exclude_regex_match`
  - `force_exclude_regex_match`
  - `include_regex_no_match`
  - `include_regex_match`
  - `outside_root_symlink`
  - `unreadable_path`
  - `ipynb_deps_missing`
  - `explicit_file`
  - `explicit_stdin`
- Specify rule ordering and short-circuit points (a truth table for file/dir + explicit/discovered).
- Decide data structures:
  - `PathDecision`
  - `RuleStep` (for traces)
  - `Ruleset` (pure evaluator)
  - `Scenario` (base + simulations)

**Acceptance criteria**

- A written spec in this file for:
  - decision types
  - reason codes + provenance types
  - evaluation ordering rules
  - simulation spec grammar (minimal, v1)
  - text + JSON output shapes
- No changes to Black runtime behavior yet.

---

### Phase 1 — Plumb flags into CLI + create scenarios

**Deliverables**

- Add flags to the CLI (`src/black/__init__.py` Click options):
  - `--explain`, `--explain-format`, `--explain-show`, `--explain-limit`, `--explain-simulate`
- Parse simulation specs into `Scenario` objects (still no discovery wiring yet).

**Acceptance criteria**

- `black --help` shows the new flags with clear descriptions and examples.
- Running `black --explain <file>` does not crash and prints at least one explain line (even if minimal).
- With `--explain` disabled, behavior and output remain unchanged (golden output tests pass).

---

### Phase 2 — Implement the ruleset evaluator (pure logic) + structured decisions

**Deliverables**

- Implement `Ruleset.evaluate(path, is_dir, context) -> PathDecision` with:
  - winner reason code + provenance
  - optional bounded trace (`RuleStep[]`) when `--explain-show trace`
- Introduce `PathDecision` storage on `Report` keyed by scenario id.
- Define “context” inputs precisely (compiled regexes, gitignore specs, root, path normalization rules).

**Acceptance criteria**

- Evaluator produces identical winner outcomes as existing logic for a representative test suite (controlled fixtures).
- `Report` can collect decisions without affecting exit codes or existing report output.
- Explain data does not affect formatting decisions (read-only unless explicitly invoked).

---

### Phase 3 — Wire explicit inputs through the ruleset (`get_sources`)

**Deliverables**

- Refactor `get_sources()` to:
  - normalize explicit args into candidate paths
  - evaluate them via `Ruleset` for each scenario (BASE + SIMs)
  - record decisions and keep existing behavior for actual sources used (BASE decision only)

**Acceptance criteria**

- `black --explain path/to/file.py` prints `INCLUDED` with a correct reason.
- `black --explain --force-exclude ... path/to/file.py` prints `IGNORED` with the force-exclude reason.
- Adding simulations does not change which files are formatted; simulations are analysis-only.

---

### Phase 4 — Wire recursive discovery through the ruleset (`gen_python_files`)

**Deliverables**

- Replace ad-hoc ignore decisions with calls into `Ruleset`, while preserving:
  - `.gitignore` layering semantics (least-specific → most-specific)
  - directory pruning behavior (don’t recurse into ignored dirs)
  - normalization differences between file/dir paths (`/` prefix, trailing `/`)
- Record decisions for both directories and files where meaningful (esp. pruned dirs).

**Acceptance criteria**

- On a directory scan, `--explain` emits decisions for both included and ignored candidates (bounded; see Phase 6).
- Explanations identify *which* mechanism ignored the path (gitignore vs regex).
- No recursion performance regression greater than an agreed threshold (see Phase 8).

---

### Phase 5 — Scenario diffing + deterministic output formatter

**Deliverables**

- Implement deterministic ordering for explain output (define and document).
- Implement scenario diffing:
  - show per-path “delta” when simulation differs from BASE winner/decision
  - aggregate per-scenario totals and “top changed reasons”
- Implement both text and JSON formatting:
  - JSON includes scenario id, decision, winner reason, provenance, and optional trace steps

**Acceptance criteria**

- Output is stable across runs on the same file tree.
- Output remains readable on Windows and POSIX paths.
- JSON output is valid and machine-parsable, with stable field names.

---

### Phase 6 — Safety valves (prevent “million-line explain”)

**Deliverables**

- Add a limit mechanism:
  - `--explain-limit N` (default e.g. 2000), or
  - auto-limit with a message (“output truncated; increase with …”).
- Ensure that `--explain` still provides useful information even when truncated:
  - include summary totals + top reasons.

**Acceptance criteria**

- Scanning a large repo does not spam unbounded output by default.
- When truncation happens, user sees:
  - that truncation occurred
  - how to raise/disable the limit

---

### Phase 7 — Tests (unit + integration)

**Deliverables**

- Add/extend tests for:
  - ruleset evaluation parity with existing behavior (BASE)
  - scenario simulation correctness (delta detection + unchanged base behavior)
  - nested `.gitignore` layering attribution (gitignore *file* provenance)
  - directory pruning explanations (ignored dir prevents recursion)
  - Windows/POSIX normalization stability (path separator handling)
- Add snapshot/golden tests for text and JSON outputs.

**Acceptance criteria**

- New tests cover all reason codes introduced in Phase 0 (each at least once) in both BASE and at least one SIM scenario.
- Existing Black tests remain green.
- Explain output tests are stable across platforms (Windows path separators accounted for).

---

### Phase 8 — Performance + correctness validation

**Deliverables**

- Micro-benchmark or profiling note demonstrating that explain collection is:
  - near-zero overhead when `--explain` is off
  - acceptable overhead when on (bounded by limits)
- Ensure thread/process interactions don’t break reporting (formatting may be parallelized; discovery decisions are typically in the main process).

**Acceptance criteria**

- `--explain` off: no measurable slowdown beyond noise on typical usage.
- `--explain` on: overhead is proportional to the number of decisions collected and respects the limit.

---

### Phase 9 — Documentation + “rule mental model”

**Deliverables**

- Add docs describing:
  - the rule ordering model (a small diagram or table)
  - how `.gitignore` interacts with CLI regexes (conceptually, without overspecifying internals)
  - how to use simulations to debug (common recipes)
  - examples (Windows + POSIX) for both text and JSON

**Acceptance criteria**

- Docs include copy-pastable examples and expected output snippets.
- Users can find the feature from `--help` and docs with minimal effort.

---

### Phase 10 — Optional: advanced simulation specs (stretch)

**Deliverables**

- Expand `--explain-simulate` spec grammar carefully (still bounded):
  - allow named scenarios: `name=...; no-gitignore; exclude+=...;`
  - allow multiple specs
  - validate and error clearly
- Add a small compatibility note about schema stability for JSON.

**Acceptance criteria**

- Simulation specs fail fast with actionable error messages.
- Advanced specs do not change BASE selection behavior.

## 🔍 Open Questions (to resolve during implementation)

- Should `--explain` default to `winner` or `trace`?
  - Recommendation: `winner` by default; `trace` is opt-in and bounded.
- How should `.gitignore` explanations attribute the rule?
  - v1: identify the `.gitignore` file that matched (not the exact rule line).
- Should we keep the existing selection logic and *also* run the ruleset in parallel for parity checks initially?
  - Recommendation: yes in early phases to prove equivalence; remove duplication once proven.

