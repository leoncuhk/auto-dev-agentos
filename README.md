# auto-dev-agentos

[![CI](https://github.com/leoncuhk/auto-dev-agentos/actions/workflows/ci.yml/badge.svg)](https://github.com/leoncuhk/auto-dev-agentos/actions) [![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Write a spec. Run the loop. Get a verified project.

A minimal [Loop Engineering](https://addyosmani.com/blog/loop-engineering) engine that replaces you as the person prompting the agent. You design the system — the system prompts the LLM, verifies the output, decides what to do next, and stops when done.

> **Core thesis**: Reliability in long-running AI agent tasks comes from *system discipline* — deterministic orchestration, stateless sessions, independent verification, hidden out-of-sample validation — not from smarter models.

## What This Is

In the language of Loop Engineering (Osmani 2026, Cherny 2026):

- The **outer loop** is `run.sh` / `run.py` — it decides what runs next
- The **inner loop** is Claude Code — it executes one task per session
- The **maker** is the LLM session — it writes code or proposes experiments
- The **checker** is the orchestrator's `verify_command` — it independently validates
- The **state** lives on disk (`.state/` JSON + markdown) — survives across sessions
- The **stop conditions** are deterministic — target met, stuck detected, budget exceeded

You write a spec (or hypothesis, or audit standards). The loop takes over.

## Architecture

![auto-dev-agentos architecture](assets/auto-dev-agentos-architecture.png)

Each session is stateless. State lives in `.state/` files. Session N+1 reads what Session N wrote. The engine decides what runs — the LLM only executes.

|              | **Engineer**         | **Researcher**        | **Auditor**              |
|--------------|----------------------|-----------------------|--------------------------|
| Input        | `spec.md`            | `hypothesis.md`       | `standards.md`           |
| Each session | One task             | One experiment        | One finding              |
| On failure   | Fix and retry        | Revert and learn      | Dismiss with evidence    |
| Exit when    | All tasks pass       | Target metric hit     | All standards covered    |
| State file   | `tasks.json`         | `journal.json`        | `findings.json`          |
| Verification | `npm test` / `pytest`| Backtest metric       | Coverage count           |

## Quick Start

```bash
git clone https://github.com/leoncuhk/auto-dev-agentos
cd auto-dev-agentos

# See what's available
./run.sh --list-modes

# Preview without invoking Claude (zero cost)
./run.sh --dry-run examples/todo-app

# Test the loop with simulation (no LLM calls, no cost)
python run.py --simulate --mode engineer --pause 0 examples/todo-app

# Write a spec, run the engine for real
mkdir my-project && echo "# My App\nBuild a REST API..." > my-project/spec.md
./run.sh my-project
```

## Prerequisites

**Shell engine** (`run.sh`):
```bash
brew install jq                         # macOS (or: apt-get install jq)
npm install -g @anthropic-ai/claude-code # Claude Code CLI
```

**SDK engine** (`run.py` — adds strategic review, hooks, cost tracking, simulation):
```bash
pip install claude-agent-sdk            # Python 3.10+
```

## Usage

```bash
# Shell engine
./run.sh [--mode <mode>] [--dry-run] <project-dir> [max-sessions]

# SDK engine
python run.py [--mode <mode>] [--dry-run] [--simulate] <project-dir> [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `engineer` | `engineer`, `researcher`, or `auditor` |
| `--dry-run` | | Preview what would run, no LLM calls |
| `--simulate` | | Use `.state/sim_script.json` for deterministic testing |
| `--max-sessions` | `50` | Session limit |
| `--max-budget` | `10.0` | Maximum cost in USD (SDK engine) |
| `--orient-interval` | `10` | Strategic review interval (SDK engine) |

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `PAUSE_SEC` | `5` | Seconds between sessions |
| `REVIEW_INTERVAL` | `5` | Tactical review every N sessions |
| `NO_PROGRESS_MAX` | `3` | Stuck detection threshold |

## Example: Researcher Mode

The [quant-lab demo](examples/quant-lab/) shows a complete research run — optimizing a trading strategy's Sharpe Ratio from 0.84 to 1.89 across 6 experiments:

| Experiment | Approach | Result | Decision |
|-----------|----------|--------|----------|
| EXP-001 | Optimize MA parameters | 0.84 → 1.37 | Accepted |
| EXP-002 | MACD confirmation | 1.37 → 0.72 | Rejected (double-lag) |
| EXP-003 | RSI position sizing | 1.37 → 1.33 | Rejected (fights trend) |
| EXP-004 | Stop-loss | Error | Reverted (framework limitation) |
| EXP-005 | Momentum + conviction sizing | 1.37 → 1.89 | Accepted — target exceeded |
| EXP-006 | Adaptive MA windows | 1.89 → 1.15 | Rejected (boundary instability) |

Failed experiments (002, 003, 004) directly informed the winning experiment (005). The loop works because failures accumulate as knowledge, not waste.

```bash
cd examples/quant-lab
python run_backtest.py                    # full data: Sharpe = 1.89
python run_backtest.py --split train      # visible to LLM: Sharpe = 1.96
python run_backtest.py --split test       # hidden OOS:     Sharpe = 1.67
```

The train/test split enables hidden out-of-sample verification — the engine independently validates on data the LLM never sees, preventing overfitting.

## Independent Verification

The engine doesn't trust LLM self-assessment. After each work session:

1. **`verify_command`** (from `mode.conf`) runs independently — the orchestrator checks the result
2. **`hidden_verify_command`** runs on hidden test data — metric written to `.state/hidden_metrics.json`, never fed back to the LLM
3. **State validation** — schema checks reject corrupt JSON before write, with automatic backup

This implements the maker-checker split: the LLM proposes, deterministic code verifies.

## Project Structure

```
auto-dev-agentos/
├── run.sh              # Shell engine (single-loop, 393 lines)
├── run.py              # SDK engine (dual-loop, simulation, 448 lines)
├── core.py             # Shared pure functions (validation, verification)
├── modes/
│   ├── engineer/       # spec.md → tasks → implement → verify
│   ├── researcher/     # hypothesis.md → experiment → evaluate → learn
│   └── auditor/        # standards.md → scan → analyze → report
├── tests/
│   ├── test_run.py     # Unit tests (17 tests)
│   └── test_integration.py  # Integration tests (30 tests)
├── docs/               # Design rationale and methodology
└── examples/           # Demo projects (todo-app, quant-lab, audit-demo)
```

## Experimental Validation

We tested three properties of the loop via simulation and deterministic backtests. Full methodology and code: [`experiments/run_validation.py`](experiments/run_validation.py).

Run it yourself: `python experiments/run_validation.py`

### What was tested

**Experiment 1 — Convergence**: Does the loop reach its target regardless of how many experiments fail along the way? Tested with 4 simulated exploration paths (lucky, typical, hard, pathological).

**Experiment 2 — Generalization**: Does the strategy discovered by the loop (on one data seed) outperform the baseline it started from when tested on 12 different random seeds?

**Experiment 3 — Autonomous correctness**: Does the engine make the right phase decision (init/work/done) across all state configurations, without human input?

### Results

| Hypothesis | Result | Key number |
|---|---|---|
| H1: Loop converges on viable paths | **Pass** | 3/3 viable paths reached target; pathological path halted by circuit breaker |
| H2: Improvement generalizes to unseen data | **Pass** | Loop-discovered strategy beats baseline on 7/12 seeds (58%) |
| H3: Autonomous decisions are correct | **Pass** | 7/7 scenarios, 100% accuracy |

**Experiment 2 detail** — strategy comparison across 12 independent random seeds (full 500-day synthetic data with 15% momentum autocorrelation):

| Metric | Baseline (dual MA crossover) | Loop-discovered (momentum + conviction) |
|---|---|---|
| Mean Sharpe | 0.13 | 0.34 |
| Positive-Sharpe rate | 58% (7/12) | 83% (10/12) |
| Beats the other | 42% | **58%** |

### What was NOT tested

- **No real LLM sessions were run.** Experiments 1 and 3 use `--simulate` mode (deterministic state-change scripts). Experiment 2 tests the quant strategy directly, not the LLM's ability to discover it.
- **The quant-lab example state was hand-crafted**, not produced by an actual run of `./run.sh --mode researcher`. A real end-to-end validation (LLM discovers the strategy from scratch) remains future work.
- **The 12-seed test uses synthetic data** with injected momentum. Real market data would provide a harder test.
- **No comparison with other agent frameworks** (DGM, OpenHands, etc.) is made here because they solve different problems at different scales — such a comparison would not be apple-to-apple.

### Interpretation

The experiments validate the **orchestration layer**: given an LLM that can improve a strategy, the loop correctly drives it from baseline to target, recovers from dead ends, and stops when appropriate. The open question remains whether the complete system (orchestration + real LLM) produces results that justify its cost in practice. This requires production runs on real projects — contributions welcome.

## Creating a New Mode

Create `modes/<name>/` with `mode.conf`, `CLAUDE.md`, and `prompts/`. The engine picks up new modes automatically. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Design Principles

These address the [six failure modes](https://arxiv.org/abs/2601.03315) of autonomous LLM agents:

| Principle | Failure mode it solves |
|-----------|----------------------|
| Stateless sessions | Context degradation — each session starts fresh |
| File-based state | Context window limits — state survives indefinitely |
| One task per session | Implementation drift — no room to simplify under pressure |
| Independent verification | Overexcitement — orchestrator verifies, not LLM self-report |
| Hidden OOS validation | Overfitting — test data invisible to the LLM |
| Circuit breaker | Infinite loops — stuck detection + max sessions + budget cap |
| Deterministic orchestration | All six — code decides flow, not LLM |
| State schema validation | Corruption — rejects invalid state, auto-backups |

## FAQ

**How much does it cost?**
Each session is one Claude Code invocation. `--dry-run` previews at zero cost. `--max-budget` caps total spend. `--simulate` runs the full loop with zero LLM calls.

**How do I test without spending money?**
Use `--simulate` mode with a `.state/sim_script.json` file. The entire orchestration loop runs identically — only the LLM call is mocked.

**Why `--dangerously-skip-permissions`?**
Headless mode — no human to click "approve." Safety comes from architecture: deterministic orchestration, one-task blast radius, git-versioned state, circuit breakers.

**Can I resume after Ctrl+C?**
Yes. Same command again. The engine re-reads `.state/` and continues from where it left off.

**Can I use a different LLM?**
Replace `claude -p` in `run.sh` with your CLI tool. The architecture is LLM-agnostic; the current implementation uses Claude.

**What's the relationship to Loop Engineering?**
This project is a Loop Engineering implementation: it replaces the human who would otherwise prompt the agent at each step. The system autonomously decides what instruction to give the LLM next, based solely on state files.

## References

**Design:**
- [Design Rationale](docs/design-rationale.md) — Why this architecture, what alternatives were considered
- [Peirce's Inquiry Cycle](docs/peirce-inquiry-cycle.md) — Why three roles per mode is logically irreducible
- [Stateless Agent Architecture](docs/stateless-agent-architecture.md) — Full argument for stateless sessions
- [Dual-Loop Architecture](docs/dual-loop-architecture.md) — Strategic orientation via OODA outer loop

**Loop Engineering:**
- [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering) — Canonical definition (June 2026)
- [Boris Cherny — Claude Code & the Future of Engineering](https://x.com/AcquiredFM/status/2062621816393297920) — "My job is to write loops" (June 2026)
- [LangChain — The Art of Loop Engineering](https://blog.langchain.dev/the-art-of-loop-engineering/) — Four-loop stack

**Research:**
- [Why LLMs Aren't Scientists Yet](https://arxiv.org/abs/2601.03315) — Six failure modes in autonomous LLM research (arXiv, 2026)
- [Building Effective AI Coding Agents](https://arxiv.org/abs/2603.05344) — Scaffolding + harness architecture (arXiv, 2026)
- [Anthropic Agentic Coding Trends](https://resources.anthropic.com/2026-agentic-coding-trends-report) — Industry landscape (2026)

**Related tools:**
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Terminal-native AI agent by Anthropic
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) — Python SDK for agent loops
- [GitHub Spec Kit](https://github.com/github/spec-kit) — Spec-driven development toolkit
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) — Full-platform autonomous coding agent
- [Omnigent](https://github.com/databricks/omnigent) — Meta-harness for composing agent loops
- [Aider](https://github.com/Aider-AI/aider) — Interactive AI pair programming
- [Sakana AI Scientist v2](https://github.com/SakanaAI/AI-Scientist-v2) — Autonomous research via tree search

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `python tests/test_run.py && python tests/test_integration.py` before submitting.

## License

AGPL-3.0. See [LICENSE](LICENSE).
