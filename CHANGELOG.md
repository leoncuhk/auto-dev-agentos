# Changelog

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
