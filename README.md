# auto-dev-agentos

**Autonomous Development Agent OS** — A minimal, mode-pluggable engine that uses LLM agents to develop projects or conduct algorithmic research autonomously.

Give it a spec (or hypothesis), let it run. Come back to a working project (or a research report).

## Architecture

```
                        ┌──────────────────────────────────┐
                        │    Universal Engine (run.sh)      │
                        │  Loop + Circuit Breaker + CLI     │
                        └───────────────┬──────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        │                               │
              ┌─────────▼─────────┐           ┌────────▼──────────┐
              │  --mode engineer  │           │ --mode researcher  │
              │  (Deductive)      │           │ (Inductive)        │
              ├───────────────────┤           ├────────────────────┤
              │ Entry: spec.md    │           │ Entry: hypothesis  │
              │ State: tasks.json │           │ State: journal.json│
              │ Pipeline:         │           │ Pipeline:          │
              │  initializer →    │           │  theorizer →       │
              │  developer →      │           │  executor →        │
              │  reviewer         │           │  analyst           │
              └───────────────────┘           └────────────────────┘
```

**Small core, pluggable brains.** The engine handles loop scheduling, session management, and circuit breaking. Mode-specific logic lives entirely in `modes/<name>/`.

## How It Works

### Engineer Mode (default)
```
spec.md  →  [Initializer]  →  tasks.json + scaffold
                                      ↓
                                [Developer]  ← loop (one task per session)
                                      ↓
                                [Reviewer]   ← every N sessions
                                      ↓
                                Complete project
```

### Researcher Mode
```
hypothesis.md  →  [Theorizer]  →  journal.json + baseline
                                        ↓
                                  [Executor]   ← loop (one experiment per session)
                                        ↓
                                  [Analyst]    ← every N sessions
                                        ↓
                                  Target metric achieved
```

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` command)
- `jq` (JSON processor)
- `git`

## Quick Start

```bash
# Engineer Mode — build a project from spec
./run.sh my-project
./run.sh --mode engineer my-project

# Researcher Mode — explore hypotheses
./run.sh --mode researcher quant-lab

# Limit sessions
./run.sh --mode engineer my-project 20

# List available modes
./run.sh --list-modes
```

## Usage

```bash
./run.sh [--mode <mode>] <project-dir> [max-sessions]
```

| Option | Description |
|--------|-------------|
| `--mode <name>` | Execution mode (default: `engineer`). Loads from `modes/<name>/` |
| `--list-modes` | List all available modes and exit |
| `<project-dir>` | Path to project directory |
| `[max-sessions]` | Max sessions to run (default: 50) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAUSE_SEC` | `5` | Seconds between sessions |
| `REVIEW_INTERVAL` | `5` | Run reviewer every N sessions |
| `NO_PROGRESS_MAX` | `3` | Consecutive no-progress sessions before abort |

## Project Structure

```
auto-dev-agentos/
├── run.sh                         # Universal engine (mode-agnostic)
├── CLAUDE.md                      # Default agent rules (fallback)
├── modes/
│   ├── engineer/                  # Deductive engineering workflow
│   │   ├── mode.conf              # Mode configuration
│   │   ├── CLAUDE.md              # Engineer-specific agent rules
│   │   └── prompts/
│   │       ├── initializer.md     # Plan + scaffold
│   │       ├── developer.md       # Implement one task
│   │       └── reviewer.md        # Periodic review
│   └── researcher/                # Inductive research workflow
│       ├── mode.conf              # Mode configuration
│       ├── CLAUDE.md              # Researcher-specific agent rules
│       └── prompts/
│           ├── theorizer.md       # Design experiment
│           ├── executor.md        # Run experiment + evaluate
│           └── analyst.md         # Periodic analysis
├── prompts/                       # Legacy prompts (deprecated)
└── examples/
    ├── todo-app/spec.md           # Engineer mode example
    └── quant-lab/hypothesis.md    # Researcher mode example
```

## Creating a New Mode

1. Create `modes/<your-mode>/mode.conf`:
   ```ini
   description=What this mode does
   entry_file=input.md
   state_file=state.json
   pending_query=[.items[] | select(.status == "pending")] | length
   progress_query=[.items[] | select(.status == "done")] | length
   phase_init=planner
   phase_work=worker
   phase_review=checker
   claude_md=CLAUDE.md
   ```

2. Create `modes/<your-mode>/CLAUDE.md` — agent workflow rules
3. Create `modes/<your-mode>/prompts/` — one `.md` per phase

That's it. The engine picks up new modes automatically.

## Design Principles

- **Minimal** — Shell script + markdown prompts. No Python framework, no complex tooling.
- **Pluggable** — New modes = new directories. Zero engine changes required.
- **Stateless sessions** — Each AI session starts fresh. All state lives in files.
- **Circuit breaker** — Stuck detection, max sessions, graceful degradation.
- **Small tasks** — Each unit of work is 10-30 minutes. Small = higher success rate.
- **Verify before done** — Every change must pass validation before marking complete.

## License

See [LICENSE](LICENSE) file.
