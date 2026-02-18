# auto-dev-agentos

**Autonomous Development Agent OS** — A minimal, professional system that uses LLM agents to develop complete projects autonomously.

Give it a spec, let it run. Come back to a working project.

## How it works

```
spec.md  →  [Initializer Agent]  →  tasks.json + project scaffold
                                          ↓
                                    [Developer Agent]  ← loop (one task per session)
                                          ↓
                                    [Reviewer Agent]   ← every N sessions
                                          ↓
                                    Complete project
```

1. **Initializer** (runs once): Reads `spec.md`, creates a task plan, scaffolds the project
2. **Developer** (runs in loop): Picks one task, implements, tests, commits — then exits. A new session starts with fresh context.
3. **Reviewer** (periodic): Analyzes progress, identifies blockers, optimizes the task list

Each session gets a clean context window. All state persists in `.state/` files.

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` command)
- `jq` (JSON processor)
- `git`

## Quick Start

```bash
# 1. Create a project directory with a spec
mkdir my-project
cp auto-dev-agentos/examples/todo-app/spec.md my-project/spec.md

# 2. Run the system
./auto-dev-agentos/run.sh my-project

# 3. (Optional) Limit sessions for testing
./auto-dev-agentos/run.sh my-project 3
```

## Usage

```bash
./run.sh <project-dir> [max-sessions]
```

| Argument | Description |
|----------|-------------|
| `project-dir` | Path to the project directory (must contain `spec.md`) |
| `max-sessions` | Optional. Max sessions to run (0 = unlimited, default) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAUSE_SEC` | `5` | Seconds between sessions |
| `REVIEW_INTERVAL` | `5` | Run reviewer every N sessions |

## Project Structure

```
auto-dev-agentos/
├── run.sh                    # Main orchestration loop
├── CLAUDE.md                 # Workflow rules (auto-read by Claude Code)
├── prompts/
│   ├── initializer.md        # First-run agent prompt
│   ├── developer.md          # Development session prompt
│   └── reviewer.md           # Periodic review prompt
└── examples/
    └── todo-app/
        └── spec.md           # Example: simple Todo app
```

### State Files (in project's `.state/`)

| File | Purpose |
|------|---------|
| `tasks.json` | Task queue with statuses |
| `progress.md` | Append-only session log |
| `features.json` | Feature verification checklist |

## Writing Your Own Spec

Create a `spec.md` in your project directory. Include:

1. **Overview** — What you're building
2. **Tech stack** — Languages, frameworks, databases
3. **Features** — User-facing features with clear acceptance criteria
4. **API/Data model** — Endpoints, schemas, data structures
5. **File structure** — Expected project layout

The more specific and concrete, the better the AI performs.

## Design Principles

- **Minimal** — Shell script + markdown prompts. No Python framework, no complex tooling.
- **Stateless sessions** — Each AI session starts fresh. All state lives in files.
- **Small tasks** — Each task is 10-30 minutes. Small = higher success rate.
- **Verify before done** — Every task must pass tests before marking complete.
- **One task per session** — Prevents context degradation over long runs.

