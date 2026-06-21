# Contributing to auto-dev-agentos

## Quick Setup

```bash
git clone https://github.com/leoncuhk/auto-dev-agentos
cd auto-dev-agentos

# Verify shell engine
./run.sh --list-modes
./run.sh --dry-run examples/todo-app

# Run all tests (47 total)
python3 tests/test_run.py           # 17 unit tests
python3 tests/test_integration.py   # 30 integration tests

# Test with simulation mode (no LLM calls)
python3 run.py --simulate --mode researcher --pause 0 examples/quant-lab
```

## Project Structure

- `run.sh` — Shell engine (v3.0, single-loop, 393 lines)
- `run.py` — SDK engine (v4.1, dual-loop + simulation, 448 lines)
- `core.py` — Shared pure functions (validation, verification, phase detection)
- `modes/<name>/` — Mode-specific logic (conf + CLAUDE.md + prompts)
- `tests/` — Unit tests + integration tests (no SDK dependency)
- `docs/` — Design rationale and methodology articles
- `examples/` — Demo projects (todo-app, quant-lab, audit-demo)

## Adding a New Mode

1. Create `modes/<name>/mode.conf`:
   ```ini
   description=What this mode does
   entry_file=input.md
   state_file=state.json
   pending_query=[.items[] | select(.status == "pending")] | length
   progress_query=[.items[] | select(.status == "done")] | length
   phase_init=planner
   phase_work=worker
   phase_review=checker
   phase_orient=strategist
   claude_md=CLAUDE.md
   verify_command=your-test-command
   hidden_verify_command=your-hidden-test-command
   ```

2. Create `modes/<name>/CLAUDE.md` — agent workflow rules
3. Create `modes/<name>/prompts/` with 3-4 prompt files:
   - `planner.md` (init phase)
   - `worker.md` (work phase)
   - `checker.md` (review phase)
   - `strategist.md` (orient phase, optional — SDK engine only)

4. Test with `--dry-run` and `--simulate`:
   ```bash
   ./run.sh --mode <name> --dry-run <project-dir>
   python3 run.py --mode <name> --simulate --pause 0 <project-dir>
   ```

## Code Style

- Shell: Follow existing `run.sh` patterns. Use `shellcheck`.
- Python: Standard library only in `core.py` and `run.py` (except `claude-agent-sdk`). No type annotations on existing code unless changing the function.
- Prompts: Markdown. Include explicit Input, Steps, Rules, and Output sections.
- Tests: Add tests for any new pure functions. Tests must not require the SDK.

## Pull Request Process

1. Fork and create a feature branch
2. Make changes
3. Run all checks:
   ```bash
   bash -n run.sh
   python3 -c "import ast; ast.parse(open('run.py').read())"
   python3 -c "import ast; ast.parse(open('core.py').read())"
   python3 tests/test_run.py
   python3 tests/test_integration.py
   ```
4. Ensure both engines stay under 500 lines each
5. Open a PR with a clear description of what changed and why

## Design Principles

Before making changes, understand the project's core thesis:

> Reliability in long-running AI agent tasks comes from system discipline — not from smarter models.

Changes should:
- Keep both engines minimal (< 500 lines each)
- Not add framework dependencies
- Maintain backward compatibility (new mode.conf keys must be ignored by run.sh)
- Prefer file-based state over in-memory state
- Prefer deterministic orchestration over LLM-driven flow control
- Include tests that prove the behavior without requiring an LLM
