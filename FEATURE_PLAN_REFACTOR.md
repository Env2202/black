## High-level refactor backlog

- **Refactor 1 (highest complexity)**: Split `src/black/__init__.py` into a clear layered architecture separating:
  - **Public API layer** (e.g. `black.api`): `format_str`, `format_file_contents`, `Mode`, partial formatting, notebook helpers.
  - **CLI layer** (e.g. `black.cli`): argument parsing, configuration loading, file discovery orchestration, exit codes.
  - **Infrastructure/runtime layer** (e.g. `black.runtime` or `black.engine`): safety checks, caching, concurrency, target-version vs runtime handling.
- **Refactor 2**: Consolidate file discovery and explain mode into a single “discovery engine”:
  - Make `ExplainReport` / `Decision` / `RulesetEvaluator` the canonical path-selection engine used by `files.py` and CLI.
  - Expose a clear API for “discover + explain” that preserves current behavior while enabling richer tooling.
- **Refactor 3**: Unify reporting, `--explain` output, and structured logging into one observability layer:
  - Introduce shared primitives for events, rendering (text / JSON / JSONL), and sinks (stdout, structured logs).
  - Refactor `output.py`, `report.py`, and explain-mode output to use these primitives.

---

## Refactor 1: Split `__init__.py` into layered architecture

### Phase 0 — Inventory & boundary design (no behavior change)

- **Instruction**
  - Survey `src/black/__init__.py` and identify:
    - Public API symbols relied on by callers and docs (functions, classes, constants).
    - CLI wiring (Click commands/options, `patched_main`, exit-code handling).
    - Formatting orchestration logic (config loading, `get_sources`, safety checks, concurrency dispatch).
  - Propose target modules and responsibilities, for example:
    - `black.api`: library-facing entrypoints and configuration objects.
    - `black.cli`: CLI command definitions and top-level orchestration.
    - `black.engine` (or `black.runtime`): core formatting pipeline orchestration that sits between API and I/O.
  - Decide which names will remain re-exported from `black.__init__` for backward compatibility.
- **Acceptance criteria**
  - A written section in this file describing:
    - The proposed modules and their responsibilities.
    - A table of symbols that must remain importable from `black` (e.g. `from black import format_str, Mode`).
    - Call graph sketch showing how CLI → engine → API should flow after refactor.
  - No code changes yet; tests and behavior remain unchanged.

---

### Phase 1 — Introduce new modules with minimal forwarding shims

- **Instruction**
  - Create new modules with initial skeletons:
    - `src/black/api.py` with thin wrappers that internally call existing implementations in `__init__.py`.
    - `src/black/cli.py` with a placeholder `main()` / `patched_main()` that delegates straight back to `black.__init__.py`.
    - `src/black/engine.py` (or chosen name) with placeholder functions for formatting orchestration.
  - Update `__init__.py` to import from these new modules, but keep the real logic in `__init__.py` for now (forwarding only).
  - Ensure `python -m black` and `black` CLI continue to work via the existing entrypoints.
- **Acceptance criteria**
  - All unit and integration tests pass with no behavioral differences.
  - New modules exist and are importable, but primarily contain pass-through shims.
  - `from black import format_str, Mode` and CLI usage remain unchanged for external users.

---

### Phase 2 — Migrate public API implementations into `black.api`

- **Instruction**
  - Move implementation of public API functions/classes from `__init__.py` into `api.py`, including:
    - `format_str`, `format_file_contents`, and any related helpers that do not depend on CLI parsing.
    - `Mode`, `TargetVersion`, and any other configuration objects that are conceptually part of the library API (if they currently live here; otherwise, align with `mode.py`).
  - Keep `__init__.py` as a backward-compatible façade:
    - Re-export API symbols from `black.api`.
    - Replace old function bodies with calls into `api.py`.
  - Adjust internal imports within the project to prefer `black.api` where appropriate, without changing external-facing imports.
- **Acceptance criteria**
  - Behavior of API calls (including preview/unstable gates and partial formatting) remains identical, verified by existing tests.
  - No circular import issues between `api.py`, `mode.py`, and other modules.
  - External code importing from `black` (root package) continues to work without modification.

---

### Phase 3 — Extract CLI wiring into `black.cli`

- **Instruction**
  - Move Click command definitions, option declarations, and `patched_main` CLI wiring from `__init__.py` into `cli.py`.
  - Keep `__init__.py` exporting the same `patched_main` symbol by importing from `black.cli`.
  - Ensure all entrypoints configured in packaging (`black` console script, `python -m black`) still resolve to the same callable.
  - Make `cli.py` delegate formatting work to `black.engine` / `black.api` rather than directly invoking low-level pieces.
- **Acceptance criteria**
  - Running `black` via CLI and `python -m black` behaves exactly as before (arguments, exit codes, help text).
  - Tests covering CLI options and error handling remain green.
  - `__init__.py` no longer contains Click decorators or argument parser definitions.

---

### Phase 4 — Introduce `black.engine` as the orchestration layer

- **Instruction**
  - Move orchestration logic out of `__init__.py` into `engine.py`, including:
    - `get_sources` integration with `files.py` and concurrency configuration.
    - Safety and stability checks wiring (AST equivalence, second-pass stability).
    - Cache use, concurrency setup, and high-level sequencing of the formatting pipeline.
  - Refactor `cli.py` and `api.py` to call into `engine.py` for actual formatting work where appropriate, keeping their interfaces stable.
  - Ensure responsibilities are clearly separated:
    - CLI: parse flags, build `Mode` / config, call engine.
    - Engine: orchestrate parsing, linegen, safety checks, I/O decisions.
    - API: thin, documented library-facing functions that configure and invoke the engine.
- **Acceptance criteria**
  - `__init__.py` no longer contains substantial orchestration logic; it primarily re-exports from `api`, `cli`, and `engine`.
  - All existing tests around file discovery, caching, and safety checks pass unchanged.
  - New or updated tests cover `engine` behavior where it is now the single place orchestrating the formatter pipeline.

---

### Phase 5 — Internal call-site cleanup and dependency tightening

- **Instruction**
  - Update internal modules that currently import from `black` root (`__init__.py`) to import from more specific modules (`black.api`, `black.cli`, `black.engine`, `black.files`, etc.) according to the new boundaries.
  - Remove any remaining internal-only helpers from `__init__.py`; keep only symbols that are intentionally part of the public API surface.
  - Ensure there is a clear layering rule documented (e.g., `engine` may depend on `parsing`, `linegen`, `files`, but not on CLI).
- **Acceptance criteria**
  - No internal module requires `black` root imports for non-public helpers; imports reflect a clean dependency graph.
  - A short layering rule description is added to this file or `OVERVIEW.md`.
  - Static analysis (if available) and tests show no new cycles or regressions.

---

### Phase 6 — Documentation and contributor guidance

- **Instruction**
  - Update `OVERVIEW.md` and any relevant contributor docs to:
    - Reflect the new module breakdown (`api`, `cli`, `engine`).
    - Describe where to add new CLI options, where to change library behavior, and where to touch orchestration logic.
  - Add a brief “for integrators” note explaining:
    - Supported import paths (`black`, `black.api`) and their stability expectations.
    - Recommendations for which surface to use when embedding Black (CLI vs API).
- **Acceptance criteria**
  - `OVERVIEW.md`’s component table and architecture diagram align with the new layering.
  - Contributors can follow documentation to locate the right module for typical changes (CLI flag vs library API vs engine behavior).
  - No references in docs suggest adding new behavior directly to `__init__.py` except for re-exports.

