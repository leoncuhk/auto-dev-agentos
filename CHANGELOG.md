# Changelog

## [4.1.0] — 2026-06-21

### Added
- **Independent verification layer**: orchestrator runs `verify_command` after each work session, independently of LLM self-report
- **Hidden out-of-sample validation**: `hidden_verify_command` in mode.conf runs on data invisible to the LLM, writes to `.state/hidden_metrics.json`
- **State schema validation**: `validate_state()` rejects corrupt/invalid state with clear error messages
- **Atomic state writes**: `safe_write_state()` validates before write, creates automatic backups, uses atomic `os.replace`
- **Budget cap**: `--max-budget` (default $10) stops the loop when cost limit is exceeded
- **Simulation mode**: `--simulate` runs the full orchestration loop using `.state/sim_script.json` — zero LLM calls, deterministic, testable
- **Train/test split**: `run_backtest.py --split train|test` with independent random seed for genuinely out-of-sample data
- **Integration tests**: 30 tests proving autonomous loop orchestration (phase transitions, circuit breaker, state validation, independent verification, full loop simulations)
- **`metric_pattern`** key in researcher mode.conf

### Changed
- `run.py` version bumped to 4.1, SDK import now optional (not required for `--simulate` or `--dry-run`)
- `core.py` expanded from 81 to 180 lines with verification and validation functions
- CI now runs integration tests alongside unit tests, with numpy/pandas for backtest verification
- README repositioned with Loop Engineering framing and verification documentation

## [4.0.0] — 2026-03-30

### Added
- **SDK engine** (`run.py`): Python alternative using Claude Agent SDK
  - Nested dual-loop architecture: outer OODA (strategic) + inner SDK (tactical)
  - `disallowed_tools` enforcement for Orient phase safety
  - `orient_edit_guard` hook restricts strategist edits to `.state/` only
  - Session cost tracking (API key mode)
  - Pure Python jq-query evaluation (no `jq` dependency)
- **Strategist prompts** for all three modes (OODA Orient phase)
  - Anti-oscillation: checks previous Orient decisions before making new ones
  - Explicit distinction from Analyst/Reviewer (prescriptive vs descriptive)
- **`--dry-run` flag** for both engines — see what would run without invoking Claude
- **Unit tests** (`tests/test_run.py`) for pure functions
- **CI** (GitHub Actions): shellcheck, Python syntax, unit tests, smoke tests
- **CONTRIBUTING.md** and issue templates
- **Methodology article**: [Dual-Loop Architecture](docs/dual-loop-architecture.md)

### Changed
- `mode.conf` now supports `phase_orient` key (backward-compatible — ignored by run.sh)
- README restructured: dual architecture diagram, SDK quick-start, updated design principles

## [3.0.0] — 2026-03-16

### Added
- **Auditor mode**: systematic codebase audit (standards → scan → findings → report)
- **Verification schema**: `acceptance_criteria` and `verify_command` fields in tasks
- **TDD workflow** in developer prompt
- **Quant-lab demo**: complete researcher mode example with 6 experiments
- **Methodology article**: [Stateless Agent Architecture](docs/stateless-agent-architecture.md)

## [2.0.0] — 2026-03-03

### Added
- **Mode system**: engineer and researcher modes with distinct workflows
- `modes/` directory structure with mode.conf, CLAUDE.md, and prompts per mode
- Researcher mode: hypothesis → experiment → evaluate → learn cycle

## [1.0.0] — 2026-02-18

### Added
- Initial release: universal engine (`run.sh`)
- Single-loop orchestration with circuit breaker
- File-based state (tasks.json, progress.md)
- Mandatory verification before commit
