# Design Rationale

Why auto-dev-agentos is designed the way it is — and what alternatives were considered.

## The Problem

Long-running LLM agent tasks fail predictably. A [2026 study](https://arxiv.org/abs/2601.03315) documented six recurring failure modes: context degradation, implementation drift, overexcitement, training data bias, insufficient domain knowledge, and weak scientific taste. Three of four autonomous research attempts in the study failed.

These are not model-specific bugs. They are structural properties of how LLMs process information over long horizons. Switching models does not fix them.

## The Design Space

We evaluated three classes of solutions:

### Multi-agent frameworks (BMAD, ChatDev, MetaGPT)

BMAD uses 26 specialized agents. ChatDev simulates a software company with CEO, CTO, programmer, tester roles. MetaGPT assigns SOPs to agents.

**Problem**: More agents = more coordination overhead. Agent-to-agent communication introduces compounding errors. The system becomes harder to debug than the code it produces. Reliability decreases as agent count increases.

### Single-session tools (Claude Code, Aider, Cursor Agent)

These tools run one LLM session that reads code, makes changes, runs tests, iterates. They work well for tasks that fit in a single context window.

**Problem**: Context degradation. After 30+ minutes, the model's attention to early instructions decays. It starts contradicting its own earlier work. Implementation drift accelerates. There is no external checkpoint to catch this.

### Platform agents (OpenHands, Devin)

Full platforms with Docker sandboxes, web GUIs, cloud execution. OpenHands has 68k+ stars. Devin handles end-to-end deployment.

**Problem**: Heavyweight. Docker dependency. Opaque orchestration. A developer cannot read and understand the control flow in 15 minutes. When something goes wrong, debugging requires understanding a complex distributed system.

## Our Choice: Deterministic Multi-Session Orchestration

auto-dev-agentos takes a fourth approach:

1. **The shell script decides what runs.** The LLM only executes single, well-scoped tasks.
2. **Each session is stateless.** Fresh context every time. No degradation.
3. **State lives in files.** JSON + markdown, git-versioned, human-readable.
4. **One task per session.** No room for drift.
5. **Verification is mandatory.** Tests and metrics decide, not the LLM.

This trades LLM autonomy for system reliability. The model is powerful but unreliable over long horizons. The shell script is simple but deterministic. Combining them produces reliability that neither achieves alone.

## What We Intentionally Do Not Do

- **No inter-agent communication.** Each session talks to files, not to other agents.
- **No persistent context.** Context windows are ephemeral; only files persist.
- **No framework dependency.** Shell + markdown + git. Runs anywhere.
- **No web UI.** CLI only. The state files *are* the interface.
- **No model routing.** One model, deterministically invoked.

Each of these is a deliberate constraint that eliminates a class of failure modes.

## The Three Modes

The same loop architecture supports three reasoning patterns:

**Engineer** — Deductive. From a spec, derive a working implementation. Exit when all tasks pass verification. This is the common case: spec-driven development.

**Researcher** — Inductive. From a hypothesis, run experiments, measure results, accumulate learnings. Failed experiments are reverted (code) but preserved (learnings). Exit when the target metric is achieved or the search space is exhausted.

**Auditor** — Abductive. From observed code patterns, hypothesize violations. Verify each with evidence. Never modify the code being audited. Exit when all standards are covered.

These three map to Peirce's inquiry cycle — each mode emphasizes one reasoning type but internally uses all three through its Init (abduction), Work (deduction), and Review (induction) phases.

## Positioning

```
Complexity ────────────────────────────────────────────►

  Claude Code     auto-dev-agentos     Gas Town        BMAD / MetaGPT
  (single session) (multi-session loop) (20-30 agents)  (26+ agents)
  
  Simple but       Simple and           Parallel but     Complex and
  degrades over    reliable over        complex          fragile
  long tasks       long tasks
```

auto-dev-agentos occupies the space between "powerful but unreliable single session" and "complex multi-agent orchestration." Minimum viable reliability for long-running autonomous tasks.

## References

- [Why LLMs Aren't Scientists Yet](https://arxiv.org/abs/2601.03315) — Six failure modes (arXiv, 2026)
- [Building Effective AI Coding Agents](https://arxiv.org/abs/2603.05344) — Scaffolding + harness architecture (arXiv, 2026)
- [Spec-Driven Development](https://github.com/github/spec-kit) — GitHub's approach to spec → code
- [BMAD Method](https://github.com/24601/BMAD-AT-CLAUDE) — 26-agent framework
- [The Stateless Agent Architecture](stateless-agent-architecture.md) — Full argument
- [The Dual-Loop Architecture](dual-loop-architecture.md) — Strategic orientation via OODA
