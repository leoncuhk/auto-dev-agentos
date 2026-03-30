# Contributing to auto-dev-agentos

## Quick Setup

```bash
git clone https://github.com/leoncuhk/auto-dev-agentos
cd auto-dev-agentos

# Verify shell engine
./run.sh --list-modes
./run.sh --dry-run examples/todo-app

# Run tests
python3 tests/test_run.py
```

## Project Structure

- `run.sh` — Shell engine (v3.0, single-loop)
- `run.py` — SDK engine (v4.0, dual-loop). Requires `pip install claude-agent-sdk`
- `modes/<name>/` — Mode-specific logic (conf + CLAUDE.md + prompts)
- `tests/` — Unit tests (no SDK dependency)
- `docs/` — Design rationale and methodology articles
- `examples/` — Demo projects

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
   ```

2. Create `modes/<name>/CLAUDE.md` — agent workflow rules
3. Create `modes/<name>/prompts/` with 3-4 prompt files:
   - `planner.md` (init phase)
   - `worker.md` (work phase)
   - `checker.md` (review phase)
   - `strategist.md` (orient phase, optional — SDK engine only)

4. Test with `--dry-run`:
   ```bash
   ./run.sh --mode <name> --dry-run <project-dir>
   ```

## Code Style

- Shell: Follow existing `run.sh` patterns. Use `shellcheck`.
- Python: Standard library only in `run.py` (except `claude-agent-sdk`). No type annotations on existing code unless changing the function.
- Prompts: Markdown. Include explicit Input, Steps, Rules, and Output sections.
- Tests: Add tests for any new pure functions. Tests must not require the SDK.

## Pull Request Process

1. Fork and create a feature branch
2. Make changes
3. Run `python3 tests/test_run.py` — all tests must pass
4. Run `bash -n run.sh` and `python3 -c "import ast; ast.parse(open('run.py').read())"` — both must pass
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
