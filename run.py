#!/usr/bin/env python3
"""
auto-dev-agentos v4.0 — SDK-based Dual-Loop Engine

Architecture: Outer OODA loop (strategic) + Inner SDK loop (tactical)
Coexists with run.sh — same mode system, additional capabilities:
  - Hooks for safety and audit / Session cost tracking
  - Pure Python (no jq dependency) / Strategic Orient phase (OODA)

Usage:
  python run.py my-project
  python run.py --mode researcher examples/quant-lab
  python run.py --simulate my-project   # deterministic mock via sim_script.json
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
VERSION = "4.1"
COMPLETE_SIGNAL = "<promise>COMPLETE</promise>"

from core import (
    load_conf, count_by_status, get_phase, progress_count,
    run_verify_command, parse_metric, safe_read_state, safe_write_state,
)

_sdk_available = False
try:
    from claude_agent_sdk import (
        query, ClaudeAgentOptions, HookMatcher, ResultMessage, AssistantMessage,
    )
    _sdk_available = True
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════
# Hooks — SDK Safety Layer
# ═══════════════════════════════════════════════════════════════

BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "git push --force", "git push -f", "DROP TABLE", "DROP DATABASE",
]


def _deny(reason: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


async def safety_guard(input_data: dict, _tool_use_id, _ctx) -> dict:
    """PreToolUse: block obviously dangerous Bash commands."""
    cmd = input_data.get("tool_input", {}).get("command", "")
    for p in BLOCKED_PATTERNS:
        if p in cmd:
            return _deny(f"Blocked: {p}")
    return {}


async def orient_edit_guard(input_data: dict, _tool_use_id, _ctx) -> dict:
    """PreToolUse: orient phase can only edit .state/ files."""
    if input_data.get("tool_name") == "Edit":
        path = input_data.get("tool_input", {}).get("file_path", "")
        if "/.state/" not in path:
            return _deny(f"Orient phase: can only edit .state/ files, not {path}")
    return {}


# ═══════════════════════════════════════════════════════════════
# Phase Configuration
# ═══════════════════════════════════════════════════════════════

PHASE_CONF = {
    "orient": {"allowed_tools": ["Read", "Glob", "Grep", "Edit"],
               "disallowed_tools": ["Bash", "Write"], "hooks": {}},
    "review": {"allowed_tools": ["Read", "Glob", "Grep", "Edit", "Bash"],
               "disallowed_tools": [], "hooks": {}},
    "default": {"allowed_tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
                "disallowed_tools": [], "hooks": {}},
}
if _sdk_available:
    PHASE_CONF["orient"]["hooks"] = {
        "PreToolUse": [HookMatcher(matcher="Edit", hooks=[orient_edit_guard])]}
    PHASE_CONF["review"]["hooks"] = {
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[safety_guard])]}
    PHASE_CONF["default"]["hooks"] = {
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[safety_guard])]}

PHASE_KEYS = {
    "init": "phase_init", "work": "phase_work",
    "review": "phase_review", "orient": "phase_orient",
}

# ═══════════════════════════════════════════════════════════════
# Session Execution — Real SDK + Simulated
# ═══════════════════════════════════════════════════════════════


async def run_session(
    project: Path, mode_dir: Path, conf: dict,
    phase: str, label: str, max_turns: int,
) -> dict:
    """Execute one agent session via SDK query()."""
    prompt_name = conf.get(PHASE_KEYS.get(phase, ""), phase)
    prompt_file = mode_dir / "prompts" / f"{prompt_name}.md"
    if not prompt_file.exists():
        return {"status": "skipped", "cost": 0.0, "turns": 0, "complete": False}

    result = {"status": "unknown", "cost": 0.0, "turns": 0, "complete": False}
    log_parts = []
    pc = PHASE_CONF.get(phase, PHASE_CONF["default"])
    opts_kwargs = dict(
        allowed_tools=pc["allowed_tools"], max_turns=max_turns,
        cwd=str(project), permission_mode="bypassPermissions", hooks=pc["hooks"],
    )
    if pc["disallowed_tools"]:
        opts_kwargs["disallowed_tools"] = pc["disallowed_tools"]

    try:
        async for msg in query(
            prompt=prompt_file.read_text(),
            options=ClaudeAgentOptions(**opts_kwargs),
        ):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if hasattr(block, "text"):
                        log_parts.append(block.text)
                        if COMPLETE_SIGNAL in block.text:
                            result["complete"] = True
            if isinstance(msg, ResultMessage):
                result["status"] = msg.subtype
                result["cost"] = msg.total_cost_usd or 0.0
                result["turns"] = msg.num_turns
                if COMPLETE_SIGNAL in (msg.result or ""):
                    result["complete"] = True
    except Exception as e:
        result["status"] = "error"
        log_parts.append(f"ERROR: {e}")

    log_dir = project / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"session_{label}.log").write_text("\n".join(log_parts))
    return result


async def run_simulated_session(
    project: Path, mode_dir: Path, conf: dict,
    phase: str, label: str, sim_script: list, sim_idx: int,
) -> dict:
    """Execute a simulated session from sim_script.json."""
    result = {"status": "success", "cost": 0.0, "turns": 1, "complete": False}
    entry = sim_script[sim_idx] if sim_idx < len(sim_script) else (
        sim_script[-1] if sim_script else None)
    if entry is None:
        return {"status": "skipped", "cost": 0.0, "turns": 0, "complete": False}

    state_changes = entry.get("state_changes", {})
    if state_changes:
        state_file = project / ".state" / conf.get("state_file", "tasks.json")
        data = {}
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
            except (json.JSONDecodeError, ValueError):
                pass
        for k, v in state_changes.items():
            data[k] = v
        state_file.write_text(json.dumps(data, indent=2) + "\n")

    result["complete"] = entry.get("complete", False)
    result["cost"] = entry.get("cost", 0.0)
    result["status"] = entry.get("status", "success")
    log_dir = project / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"session_{label}.log").write_text(
        f"[SIMULATE] phase={phase} entry={json.dumps(entry)}")
    return result


async def run_cli_session(
    project: Path, mode_dir: Path, conf: dict,
    phase: str, label: str, max_turns: int,
) -> dict:
    """Execute one agent session via claude CLI (no SDK needed)."""
    prompt_name = conf.get(PHASE_KEYS.get(phase, ""), phase)
    prompt_file = mode_dir / "prompts" / f"{prompt_name}.md"
    if not prompt_file.exists():
        return {"status": "skipped", "cost": 0.0, "turns": 0, "complete": False}

    result = {"status": "unknown", "cost": 0.0, "turns": 0, "complete": False}
    try:
        proc = subprocess.run(
            ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "text"],
            input=prompt_file.read_text(), capture_output=True, text=True,
            cwd=str(project), timeout=600,
        )
        output = proc.stdout
        result["status"] = "success" if proc.returncode == 0 else "error"
        result["turns"] = 1
        if COMPLETE_SIGNAL in output:
            result["complete"] = True
    except subprocess.TimeoutExpired:
        output = ""
        result["status"] = "timeout"
    except Exception as e:
        output = f"ERROR: {e}"
        result["status"] = "error"

    log_dir = project / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"session_{label}.log").write_text(output[-5000:])
    return result


# ═══════════════════════════════════════════════════════════════
# Verification — Orchestrator-Enforced
# ═══════════════════════════════════════════════════════════════


def run_post_session_verification(project: Path, conf: dict, phase: str,
                                  session: int, log_prefix: str = ""):
    """Run verify_command and hidden_verify_command after work sessions."""
    if phase != "work":
        return
    verify_cmd = conf.get("verify_command", "")
    if verify_cmd:
        vr = run_verify_command(str(project), verify_cmd)
        if not vr["success"]:
            print(f"{log_prefix}[{ts()}] WARNING: Verification failed "
                  f"- LLM may have reported false success (exit {vr['exit_code']})")
    hidden_cmd = conf.get("hidden_verify_command", "")
    if hidden_cmd:
        hr = run_verify_command(str(project), hidden_cmd)
        metrics_path = project / ".state" / "hidden_metrics.json"
        existing = []
        if metrics_path.exists():
            try:
                existing = json.loads(metrics_path.read_text())
            except (json.JSONDecodeError, ValueError):
                existing = []
        existing.append({"session": session, "metric": hr.get("metric"),
                         "timestamp": datetime.now(timezone.utc).isoformat()})
        metrics_path.write_text(json.dumps(existing, indent=2) + "\n")


# ═══════════════════════════════════════════════════════════════
# Dual-Loop Engine
# ═══════════════════════════════════════════════════════════════

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def engine(args):
    """Nested dual-loop: outer OODA (strategic) + inner SDK (tactical)."""
    simulate = getattr(args, "simulate", False)
    log_prefix = "[SIMULATE] " if simulate else ""

    mode_dir = SCRIPT_DIR / "modes" / args.mode
    if not mode_dir.is_dir():
        avail = [d.name for d in (SCRIPT_DIR / "modes").iterdir() if d.is_dir()]
        sys.exit(f"Mode '{args.mode}' not found. Available: {', '.join(avail)}")

    conf = load_conf(mode_dir)
    project = Path(args.project_dir).resolve()
    project.mkdir(parents=True, exist_ok=True)
    (project / ".state").mkdir(exist_ok=True)
    (project / "logs").mkdir(exist_ok=True)

    entry = conf.get("entry_file", "spec.md")
    if not (project / entry).exists():
        sys.exit(f"No {entry} in {project}. Required for --mode {args.mode}.")

    if not (project / "CLAUDE.md").exists():
        src = mode_dir / conf.get("claude_md", "CLAUDE.md")
        if not src.exists():
            src = SCRIPT_DIR / "CLAUDE.md"
        if src.exists():
            (project / "CLAUDE.md").write_text(src.read_text())

    state_path = project / ".state" / conf.get("state_file", "tasks.json")

    # Load simulation script
    sim_script, sim_idx = [], 0
    if simulate:
        sim_path = project / ".state" / "sim_script.json"
        if not sim_path.exists():
            sys.exit(f"[SIMULATE] No sim_script.json in {project / '.state'}")
        sim_script = json.loads(sim_path.read_text())

    # ── Banner ──
    print(f"\n  {'='*52}")
    print(f"       auto-dev-agentos v{VERSION} (SDK Engine)")
    print(f"    Nested Dual-Loop: OODA x SDK")
    if simulate:
        print(f"    [SIMULATE MODE - deterministic mock]")
    print(f"  {'='*52}\n")
    print(f"  {log_prefix}Mode    : {args.mode}")
    print(f"  {log_prefix}Project : {project}")
    print(f"  {log_prefix}Sessions: max {args.max_sessions} | Budget: ${args.max_budget:.2f}")
    print(f"  {log_prefix}Review  : every {args.review_interval} | Orient: every {args.orient_interval}\n")

    if args.dry_run:
        print(f"  [DRY RUN] No agents will be invoked.\n")
        phase = get_phase(state_path, conf)
        done = progress_count(state_path, conf)
        total = done
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                for key in ["tasks", "experiments", "findings"]:
                    if key in data:
                        total = len(data[key])
                        break
            except (json.JSONDecodeError, ValueError):
                pass
        print(f"  Phase     : {phase}")
        print(f"  Progress  : {done}/{total} completed")
        print(f"  Entry file: {entry} {'(exists)' if (project / entry).exists() else '(MISSING)'}")
        print(f"  State file: {conf.get('state_file', 'tasks.json')} "
              f"{'(exists)' if state_path.exists() else '(will be created)'}")
        prompt_name = conf.get(PHASE_KEYS.get(phase, ""), phase)
        prompt_file = mode_dir / "prompts" / f"{prompt_name}.md"
        print(f"  Next prompt: {prompt_file.name} {'(exists)' if prompt_file.exists() else '(MISSING)'}")
        pc = PHASE_CONF.get(phase, PHASE_CONF["default"])
        print(f"  Tools     : {', '.join(pc['allowed_tools'])}")
        if pc.get("disallowed_tools"):
            print(f"  Blocked   : {', '.join(pc['disallowed_tools'])}")
        return

    session, no_progress, total_cost = 0, 0, 0.0

    # ── Main Loop ──
    while True:
        session += 1
        if session > args.max_sessions:
            print(f"{log_prefix}[{ts()}] Max sessions ({args.max_sessions}). Stopping.")
            break

        phase = get_phase(state_path, conf)
        if phase == "done":
            print(f"{log_prefix}[{ts()}] All work complete!")
            break

        # ── OODA Orient (strategic review) ──
        if session > 1 and session % args.orient_interval == 0:
            print(f"\n{log_prefix}[{ts()}] == OODA Orient ==")
            if simulate:
                r = await run_simulated_session(
                    project, mode_dir, conf, "orient", f"orient_{session}",
                    sim_script, sim_idx)
                sim_idx += 1
            elif _sdk_available:
                r = await run_session(
                    project, mode_dir, conf, "orient", f"orient_{session}", 15)
            else:
                r = await run_cli_session(
                    project, mode_dir, conf, "orient", f"orient_{session}", 15)
            total_cost += r["cost"]
            if r["status"] != "skipped":
                print(f"{log_prefix}[{ts()}] Orient: {r['status']} | ${r['cost']:.4f}")
            phase = get_phase(state_path, conf)
            if phase == "done":
                print(f"{log_prefix}[{ts()}] Orient determined: complete!")
                break

        prev = progress_count(state_path, conf)

        if phase == "work":
            init_script = project / "init.sh"
            if init_script.exists():
                subprocess.run(["bash", str(init_script)], cwd=str(project),
                               capture_output=True, timeout=60)

        # ── Tactical Session ──
        print(f"\n{log_prefix}[{ts()}] Session #{session} -- {phase} [{args.mode}]")
        if simulate:
            r = await run_simulated_session(
                project, mode_dir, conf, phase, str(session), sim_script, sim_idx)
            sim_idx += 1
        elif _sdk_available:
            r = await run_session(
                project, mode_dir, conf, phase, str(session), args.max_turns)
        else:
            r = await run_cli_session(
                project, mode_dir, conf, phase, str(session), args.max_turns)
        total_cost += r["cost"]
        print(f"{log_prefix}[{ts()}] #{session}: {r['status']} | "
              f"${r['cost']:.4f} | {r['turns']} turns | total ${total_cost:.4f}")

        if r["complete"]:
            print(f"{log_prefix}[{ts()}] Agent confirmed complete!")
            break

        # ── Budget Cap ──
        if total_cost >= args.max_budget:
            print(f"{log_prefix}[{ts()}] Budget cap reached "
                  f"(${total_cost:.4f} >= ${args.max_budget:.2f}). Stopping.")
            break

        # ── Orchestrator Verification ──
        run_post_session_verification(project, conf, phase, session, log_prefix)

        # ── Circuit Breaker ──
        if phase == "work":
            curr = progress_count(state_path, conf)
            if curr <= prev:
                no_progress += 1
                print(f"{log_prefix}[{ts()}] No progress ({no_progress}/{args.no_progress_max})")
                if no_progress >= args.no_progress_max:
                    print(f"{log_prefix}[{ts()}] Stuck. Stopping.")
                    break
            else:
                no_progress = 0

        # ── Tactical Review ──
        if session >= args.review_interval and session % args.review_interval == 0:
            print(f"\n{log_prefix}[{ts()}] == Tactical Review ==")
            if simulate:
                r = await run_simulated_session(
                    project, mode_dir, conf, "review", f"review_{session}",
                    sim_script, sim_idx)
                sim_idx += 1
            elif _sdk_available:
                r = await run_session(
                    project, mode_dir, conf, "review", f"review_{session}", 20)
            else:
                r = await run_cli_session(
                    project, mode_dir, conf, "review", f"review_{session}", 20)
            total_cost += r["cost"]
            print(f"{log_prefix}[{ts()}] Review: {r['status']} | ${r['cost']:.4f}")

        await asyncio.sleep(args.pause)

    print(f"\n{log_prefix}[{ts()}] Done. {args.mode} | {session} sessions | ${total_cost:.4f}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    p = argparse.ArgumentParser(
        description=f"auto-dev-agentos v{VERSION} -- SDK Dual-Loop Engine")
    p.add_argument("project_dir", nargs="?", help="Project directory")
    p.add_argument("--mode", default="engineer", help="Execution mode (default: engineer)")
    p.add_argument("--max-sessions", type=int, default=50)
    p.add_argument("--max-turns", type=int, default=50, help="Max LLM turns per session")
    p.add_argument("--max-budget", type=float, default=10.0,
                   help="Max total cost in USD (default: 10.0)")
    p.add_argument("--review-interval", type=int, default=5)
    p.add_argument("--orient-interval", type=int, default=10)
    p.add_argument("--no-progress-max", type=int, default=3)
    p.add_argument("--pause", type=int, default=5, help="Seconds between sessions")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--simulate", action="store_true",
                   help="Use .state/sim_script.json instead of real LLM calls")
    p.add_argument("--list-modes", action="store_true")
    args = p.parse_args()

    if args.list_modes:
        print("Available modes:")
        for d in sorted((SCRIPT_DIR / "modes").iterdir()):
            if d.is_dir():
                c = load_conf(d)
                print(f"  {d.name} -- {c.get('description', '(no description)')}")
        return

    if not args.project_dir:
        p.print_help()
        return

    if not args.simulate and not args.dry_run and not _sdk_available:
        # No SDK — fall back to claude CLI (same as run.sh but with verify support)
        try:
            subprocess.run(["claude", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            sys.exit("Neither claude-agent-sdk nor claude CLI found.\n"
                     "  Install SDK: pip install claude-agent-sdk\n"
                     "  Or install CLI: npm install -g @anthropic-ai/claude-code\n"
                     "  Or use --simulate for testing without either.")

    asyncio.run(engine(args))


if __name__ == "__main__":
    main()
