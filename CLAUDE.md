# auto-dev-agentos — Project Instructions

> Auto-read by Claude Code when working on this repository.

## What This Project Is

A minimal, mode-pluggable engine for autonomous LLM agent tasks. Two engines:
- `run.sh` (~380 lines of shell) — single-loop, zero dependencies
- `run.py` (~400 lines of Python) — dual-loop with SDK hooks

## Architecture

- `core.py` — shared pure functions (config loading, phase detection, status counting)
- `run.sh` / `run.py` — engines (orchestration loop, session execution)
- `modes/<name>/` — mode-specific logic (mode.conf + CLAUDE.md + prompts/)
- `tests/test_run.py` — unit tests for core.py functions

## Working on This Codebase

- Run tests: `python3 tests/test_run.py`
- Syntax check: `bash -n run.sh && python3 -c "import ast; ast.parse(open('run.py').read())"`
- Smoke test: `./run.sh --dry-run examples/todo-app`
- Both engines must stay under 500 lines each
- New mode.conf keys must be ignored by run.sh (backward compatibility)
- Pure functions go in core.py, not in run.py

## Key Design Rules

1. **Stateless sessions** — each LLM call starts fresh, state lives in files
2. **Deterministic orchestration** — shell/Python decides flow, not LLM
3. **One task per session** — no multi-task sessions
4. **Mandatory verification** — metrics decide, not LLM self-assessment
5. **Minimal** — no frameworks, no Docker, no magic
