# auto-dev-agentos

**Autonomous Development Agent OS** — A minimal, mode-pluggable engine that uses LLM agents to develop projects, conduct algorithmic research, or audit codebases autonomously.

Give it a spec (or hypothesis, or standards doc), let it run. Come back to a working project (or research report, or audit report).

> **Core thesis**: Reliability in long-running AI agent tasks comes from *system discipline* — deterministic orchestration, stateless sessions, file-based state, mandatory verification — not from smarter models. See [the methodology article](articles/stateless-agent-architecture.md) for the full argument.

## Architecture

```
                        ┌──────────────────────────────────┐
                        │    Universal Engine (run.sh)      │
                        │  Loop + Circuit Breaker + CLI     │
                        └───────────────┬──────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
    │  --mode engineer  │   │ --mode researcher   │   │  --mode auditor   │
    │  (Deductive)      │   │ (Inductive)         │   │  (Systematic)     │
    ├───────────────────┤   ├─────────────────────┤   ├───────────────────┤
    │ Entry: spec.md    │   │ Entry: hypothesis.md│   │ Entry: standards  │
    │ State: tasks.json │   │ State: journal.json │   │ State: findings   │
    │ Pipeline:         │   │ Pipeline:           │   │ Pipeline:         │
    │  initializer →    │   │  theorizer →        │   │  scanner →        │
    │  developer →      │   │  executor →         │   │  auditor →        │
    │  reviewer         │   │  analyst            │   │  reporter         │
    └───────────────────┘   └─────────────────────┘   └───────────────────┘
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

### Auditor Mode
```
standards.md  →  [Scanner]  →  findings.json + initial scan
                                      ↓
                                [Auditor]   ← loop (one finding per session)
                                      ↓
                                [Reporter]  ← every N sessions
                                      ↓
                                Audit report generated
```

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` command)
- `jq` (JSON processor)
- `git`

## Quick Start

```bash
# Engineer: build a project from spec
./run.sh my-project

# Researcher: run the quant-lab demo
cd examples/quant-lab && python run_backtest.py  # verify baseline
cd ../.. && ./run.sh --mode researcher examples/quant-lab

# Auditor: audit a codebase against standards
./run.sh --mode auditor examples/audit-demo

# Limit sessions / list modes
./run.sh --mode engineer my-project 20
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
│   ├── researcher/                # Inductive research workflow
│   │   ├── mode.conf
│   │   ├── CLAUDE.md
│   │   └── prompts/
│   │       ├── theorizer.md       # Design experiment
│   │       ├── executor.md        # Run experiment + evaluate
│   │       └── analyst.md         # Periodic analysis
│   └── auditor/                   # Systematic audit workflow
│       ├── mode.conf
│       ├── CLAUDE.md
│       └── prompts/
│           ├── scanner.md         # Scan codebase for findings
│           ├── auditor.md         # Deep-analyze one finding
│           └── reporter.md        # Generate audit report
├── articles/                      # Methodology & design rationale
├── prompts/                       # Legacy prompts (deprecated)
└── examples/
    ├── todo-app/spec.md           # Engineer mode example
    ├── quant-lab/                  # Researcher mode example (complete demo)
    │   ├── hypothesis.md          # Research goals
    │   ├── run_backtest.py        # Runnable backtest script
    │   ├── strategies.py          # Strategy implementations
    │   └── .state/                # Pre-populated experiment journal
    └── audit-demo/standards.md    # Auditor mode example
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

These principles address the [six failure modes](https://arxiv.org/abs/2601.03315) documented in autonomous LLM research:

| Principle | Addresses | How |
|-----------|-----------|-----|
| **Stateless sessions** | Context degradation | Each session starts fresh; no accumulated confusion |
| **File-based state** | Context degradation | State survives across sessions without context window limits |
| **One task per session** | Implementation drift | No room to progressively simplify under pressure |
| **Mandatory verification** | Overexcitement | Metrics decide, not the LLM's self-assessment |
| **Circuit breaker** | Infinite loops | Stuck detection + max sessions prevent runaway execution |
| **Deterministic orchestration** | All six failure modes | Shell script decides flow, not LLM — predictable, auditable |
| **Mode-pluggable** | — | New workflows = new directories, zero engine changes |
| **Minimal** | — | 334 lines of shell + markdown prompts. No framework lock-in |

## Further Reading

- [**Methodology article**](articles/stateless-agent-architecture.md): Why stateless sessions and deterministic orchestration solve the reliability problem in long-running AI agent tasks
- [**Quant-lab demo**](examples/quant-lab/): Complete researcher mode example with 6 experiments, journal, and progress log

## License

See [LICENSE](LICENSE) file.
