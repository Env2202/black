# OVERVIEW

## 🧭 Purpose & Scope

Black is an **opinionated, deterministic Python code formatter**. It reformats Python source (and optionally Jupyter notebooks) into a consistent style with deliberately limited configuration.

- **Problem it solves**: Eliminates manual formatting debates and churn by producing stable, review-friendly diffs and consistent code style across teams and projects.
- **Who the users are**:
  - Application/library developers who want automatic formatting.
  - Tooling integrators (editors, CI, pre-commit hooks) calling Black programmatically.
  - Teams and platforms that need formatting-as-a-service (via `blackd`).
- **Why it matters**:
  - Reduces cognitive overhead and code review noise.
  - Improves consistency across large codebases and contributor pools.
  - Provides safety checks (by default) to ensure formatted code is AST-equivalent.


| Purpose                            | Scope                                                                              | Notes                                                                   |
| ---------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Deterministic formatting of Python | CLI (`black`), programmatic API (`black.format_str`, `black.format_file_contents`) | Defaults are “sensible”; configuration is intentionally constrained.    |
| Apply formatting to real projects  | File discovery, include/exclude handling, `.gitignore` integration, caching        | Uses `pyproject.toml` (`[tool.black]`) as the primary config mechanism. |
| Safety and stability guarantees    | AST equivalence and “stable on second pass” checks (unless `--fast`)               | Safety checks are a key part of Black’s value proposition.              |
| Optional service mode              | HTTP formatting service via `blackd`                                               | Requires extras (`black[d]`) and uses `aiohttp`.                        |


## 🏛️ Architecture

### High-level flow

At a high level, Black works as a pipeline:

1. **Entry point**: `black:patched_main` (CLI) or `blackd` (HTTP service)
2. **Configuration & source selection**:
  - Load config from `pyproject.toml` (or user-level config)
  - Discover sources via explicit paths, recursive directory walk, and `.gitignore` rules
3. **Read & decode inputs**:
  - Detect encoding + newline style
  - Special handling for stdin, `.pyi`, and `.ipynb`
4. **Format**:
  - Parse to a syntax tree (lib2to3-based)
  - Generate formatted “lines”
  - Apply splitting/transform rules to satisfy the configured line length and style options
5. **Validate (default “safe” mode)**:
  - Ensure AST-equivalent output
  - Ensure a second formatting pass yields identical output (stability)
6. **Write-back / diff / check**:
  - Write in-place, emit diff, or exit with status code

### Mermaid architecture diagram

```mermaid
flowchart TD
  %% External actors
  U[User / CI / Editor] -->|runs| CLI[CLI: black (black:patched_main)]
  UC[User Codebase] -->|files| CLI
  U -->|HTTP requests| SVC[Service: blackd]

  %% Public API
  API[Public API: black.format_str / black.format_file_contents / black.Mode]:::pub
  CLI --> API
  SVC -->|calls| API

  %% Readers / Writers
  subgraph IO[Readers / Writers]
    DISC[File discovery: black.files\nfind_project_root / gen_python_files]
    CFG[Config: pyproject.toml\nblack.files.parse_pyproject_toml]
    DEC[Decode: encoding + newline\nblack.decode_bytes]
    WB[Write-back / Diff / Report\nblack.format_file_in_place + black.output + black.report]
    CACHE[Cache: black.cache]
  end

  CLI --> DISC
  CLI --> CFG
  DISC -->|paths| DEC
  DEC -->|src text| API
  API --> WB
  WB --> CACHE

  %% Core formatting pipeline
  subgraph CORE[Core formatting pipeline]
    PARSE[Parse: black.parsing.lib2to3_parse\n(grammars by target versions)]
    MODEL[Data model: black.mode.Mode\nTargetVersion / Preview / Feature]
    LINEGEN[Line generation: black.linegen.LineGenerator]
    XFORM[Transforms & splitting: black.linegen.transform_line\n+ brackets/strings/comments/etc.]
    VALID[Validation (safe):\nassert_equivalent + assert_stable]
  end

  API --> MODEL
  API --> PARSE
  PARSE --> LINEGEN
  LINEGEN --> XFORM
  XFORM -->|formatted text| VALID
  VALID -->|final text| WB

  %% Utilities
  subgraph UTIL[Utilities]
    OUT[Output helpers: black.output]
    RANGES[Partial formatting: black.ranges]
    NB[Jupyter helpers: black.handle_ipynb_magics]
  end
  WB --> OUT
  API --> RANGES
  API --> NB

  classDef pub fill:#111,stroke:#111,color:#fff;
```



### Component table


| Component                                     | Description                                                                                                                                                                 |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/black/__init__.py`                       | Primary module: CLI wiring, config loading, file selection (`get_sources`), and core formatting entrypoints (`format_str`, `format_file_contents`, `format_file_in_place`). |
| `src/black/__main__.py`                       | `python -m black` entrypoint that dispatches to `patched_main()`.                                                                                                           |
| `src/black/mode.py`                           | **Core configuration model**: `Mode`, `TargetVersion`, feature flags, preview/unstable feature gates, cache key derivation.                                                 |
| `src/black/files.py`                          | Project root detection, `pyproject.toml` parsing/inference, `.gitignore` integration, include/exclude filtering, recursive file discovery.                                  |
| `src/black/parsing.py`                        | Parsing (lib2to3 grammars) + AST parsing helpers for safety checks and error reporting.                                                                                     |
| `src/black/linegen.py`                        | The heart of formatting: converts parse trees to formatted `Line`s and applies splitting/transformation logic.                                                              |
| `src/black/lines.py`                          | Line representation (`Line`, blocks) and helpers used by the generator and transformers.                                                                                    |
| `src/black/output.py` / `src/black/report.py` | User-visible output: diffs, colored diffs, progress/reporting, exit codes, messaging.                                                                                       |
| `src/black/cache.py`                          | Cache read/write to skip unchanged files (when allowed by write-back mode).                                                                                                 |
| `src/black/handle_ipynb_magics.py`            | Notebook-specific handling: masks IPython magics, formats code cells, restores magics; handles notebook-specific diff output.                                               |
| `src/black/concurrency.py`                    | Parallel formatting orchestration and event-loop helpers (e.g. uvloop integration).                                                                                         |
| `src/blackd/`*                                | HTTP service wrapper around Black for formatting as a service (uses `aiohttp`, optional via extras).                                                                        |
| `src/blib2to3/*`                              | Vendored parsing infrastructure used by Black’s formatter pipeline.                                                                                                         |


## ⚖️ Pain Points / Trade-offs

Black is stable and battle-tested, but there are inherent trade-offs in a formatter that must be correct, deterministic, and fast.


| Area                                                               | Impact                                                                         | Notes                                                                                                                               |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Parser dependency on lib2to3-derived grammar (`blib2to3`)          | **Brittle around new syntax** and harder evolution of grammar support          | Black mitigates by selecting grammars based on target versions, but grammar updates remain non-trivial.                             |
| Formatting pipeline complexity (`LineGenerator` + many transforms) | **High cognitive load** for contributors; changes can have wide ripple effects | Split/transform rules interact (brackets, strings, comments, trailing commas, optional parens). Small tweaks can affect many cases. |
| Safety + stability checks (`assert_equivalent`, `assert_stable`)   | **Performance cost** and occasional “environment mismatch” confusion           | Safe mode is valuable, but can be slow; parsing for AST equivalence depends on runtime Python capabilities vs target versions.      |
| Mixed concerns in `src/black/__init__.py`                          | **Harder navigation** and “god module” feel                                    | It hosts CLI wiring, core formatting functions, config parsing hooks, and parts of the IO pipeline.                                 |
| `.gitignore` + exclude/include semantics                           | **User confusion** when results differ by invocation method                    | Behavior differs between recursive discovery and explicit file args; `--force-exclude` adds another dimension.                      |
| Notebook formatting path (`.ipynb`)                                | **Different operational model** (cell-by-cell JSON) + dependency gating        | Requires optional deps; differs from `.py` formatting, with its own validation and diff behavior.                                   |
| Preview/unstable feature gating                                    | **Behavior matrix** grows over time                                            | `Mode.__contains__` blends `preview`, `unstable`, and explicit feature enables, which can be tricky to reason about.                |
| Optional compilation (mypyc)                                       | **Different runtime behavior** and debugging ergonomics                        | Some modules are excluded from compilation; compiled vs non-compiled builds require careful testing and packaging discipline.       |


## 🚀 Potential Enhancements

All suggestions below are intended to be realistic in a mature, widely-used formatter (i.e., conservative, test-driven changes).


| Priority | Idea                                                                                                     | Component                                             | Quick-Win? |
| -------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------- |
| High     | Improve “target version vs runtime version” messaging with clearer remediation and context               | `src/black/__init__.py` safety checks + CLI output    | Yes        |
| High     | Strengthen “format a subset of lines” UX (clearer limitations and more robust stable-check strategy)     | `src/black/ranges.py`, `format_str` / `assert_stable` | No         |
| High     | Add a documented “internal architecture map” for contributors (module roles + common change workflows)   | Docs + `src/black/`*                                  | Yes        |
| Medium   | Performance profiling harness or documented workflow for hotspots (transformers / parsing)               | `src/black/linegen.py`, `src/black/parsing.py`        | Yes        |
| Medium   | Cleaner separation between CLI wiring and library API (reduce `__init__.py` surface area)                | `src/black/__init__.py`                               | No         |
| Medium   | More explicit layering for notebook support (clear boundaries between JSON handling and core formatting) | `src/black/handle_ipynb_magics.py`                    | No         |
| Medium   | Add structured logging hooks for integrations (optional)                                                 | `src/black/report.py`, `src/black/output.py`          | No         |
| Low      | Add “explain why file is ignored” output mode that aggregates decisions                                  | `src/black/files.py`, `src/black/report.py`           | No         |
| Low      | Expand `blackd` operational docs (timeouts, concurrency knobs, deployment patterns)                      | `src/blackd/*` + docs                                 | Yes        |


## 🧰 Onboarding Guidance

### Local setup (developer workflow)

This repository is packaged via `pyproject.toml` and tested via `tox`. The simplest “I can run Black from source” setup is an editable install.

1. **Create and activate a virtual environment**

```bash
python -m venv .venv
```

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

1. **Install the project (editable)**

```bash
python -m pip install -U pip
python -m pip install -e .
```

1. **Run Black from the repo**

```bash
black --version
```

Expected output resembles:

```text
black, <version> (compiled: <yes|no>)
Python (<impl>) <runtime-version>
```

1. **Format something**

```bash
black path\to\your_package
```

Expected happy-path ending resembles:

```text
All done! ✨ 🍰 ✨
```

1. **Run the test suite via tox**

```bash
tox -e py313
```

Notes:

- Tox uses `isolated_build = true` and installs extras in phases (notably Jupyter-related tests).
- A “format this repo” check exists:

```bash
tox -e run_self
```

### Container workflow (Docker)

This repo includes a `Dockerfile` that builds a wheel (with Hatch) and installs Black into a slim runtime image.

1. **Build**

```bash
docker build -t black:dev .
```

1. **Run Black inside the container**

```bash
docker run --rm black:dev --version
```

1. **Format your working directory**

```bash
docker run --rm -v "%cd%:/work" -w /work black:dev black .
```

Expected output resembles:

```text
All done! ✨ 🍰 ✨
```

### Running `blackd` (formatting as a service)

`blackd` is optional and requires the `d` extra (it uses `aiohttp`).

1. **Install with the extra**

```bash
python -m pip install -e ".[d]"
```

1. **Run the service**

```bash
python -m blackd --bind-host localhost --bind-port 45484
```

Expected output resembles:

```text
blackd version <version> listening on localhost port 45484
```

### Tips for exploring and extending the codebase

- **Start at the pipeline boundaries**:
  - File selection/config: `src/black/files.py`
  - Primary orchestration and public entrypoints: `src/black/__init__.py`
  - Core formatting mechanics: `src/black/linegen.py` and `src/black/lines.py`
- **When changing formatting behavior**:
  - Expect broad impact; use targeted tests and be mindful of preview/unstable gating (`src/black/mode.py`).
  - Keep “safe mode” invariants in mind: AST equivalence and stability are fundamental contract points.
- **When debugging “why is this file ignored?”**:
  - The ignore stack is typically: `.gitignore` → `--exclude` → `--extend-exclude` → `--force-exclude`, plus include regex filtering.
- **When touching notebooks**:
  - Notebook formatting is cell-based and involves masking/unmasking IPython magics (`src/black/handle_ipynb_magics.py`).

