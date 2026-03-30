#!/usr/bin/env python3
"""
auto-dev-agentos v4.0 — SDK-based Dual-Loop Engine

Architecture: Outer OODA loop (strategic) + Inner SDK loop (tactical)
Coexists with run.sh — same mode system, additional capabilities:
  - Hooks for safety and audit
  - Session cost tracking
  - Pure Python (no jq dependency)
  - Strategic Orient phase (OODA)

Prerequisites:
  pip install claude-agent-sdk
  # Or: already logged into Claude Code (subscription auth)

Usage:
  python run.py my-project
  python run.py --mode researcher examples/quant-lab
  python run.py --mode auditor examples/audit-demo
  python run.py --list-modes
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        HookMatcher,
        ResultMessage,
        AssistantMessage,
    )
except ImportError:
    sys.exit(
        "claude-agent-sdk not found.\n"
        "  Install: pip install claude-agent-sdk\n"
        "  Or use run.sh for the shell-based engine."
    )

SCRIPT_DIR = Path(__file__).parent
VERSION = "4.0"
COMPLETE_SIGNAL = "<promise>COMPLETE</promise>"

# Pure utility functions (shared with tests via core.py)
from core import load_conf, count_by_status, get_phase, progress_count


# ═══════════════════════════════════════════════════════════════
# Hooks — SDK Safety Layer
#
# NOTE ON SECURITY MODEL:
# safety_guard uses literal substring matching. It catches accidental
# dangerous commands but is trivially bypassable (flag reordering,
# variable expansion, nested shells, etc.). It is NOT a security
# boundary. For production use, run in a sandboxed container.
# The real safety comes from: deterministic orchestration (LLM doesn't
# control flow), one-task-per-session (blast radius is small), and
# git-versioned state (everything is reversible).
# ═══════════════════════════════════════════════════════════════

BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "git push --force", "git push -f",
    "DROP TABLE", "DROP DATABASE",
]


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


async def safety_guard(input_data: dict, _tool_use_id, _ctx) -> dict:
    """PreToolUse: block obviously dangerous Bash commands (best-effort)."""
    cmd = input_data.get("tool_input", {}).get("command", "")
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd:
            return _deny(f"Blocked: {pattern}")
    return {}


async def orient_edit_guard(input_data: dict, _tool_use_id, _ctx) -> dict:
    """PreToolUse: during orient phase, restrict Edit to .state/ files only."""
    tool = input_data.get("tool_name", "")
    if tool == "Edit":
        path = input_data.get("tool_input", {}).get("file_path", "")
        if "/.state/" not in path:
            return _deny(f"Orient phase: can only edit .state/ files, not {path}")
    return {}


# ═══════════════════════════════════════════════════════════════
# Session Execution — Inner SDK Loop
# ═══════════════════════════════════════════════════════════════

# Phase-specific tool configuration.
# NOTE: Under bypassPermissions, allowed_tools does NOT restrict access —
# all tools are available. Use disallowed_tools to enforce hard blocks.
# See: SDK permission chain — disallowed_tools overrides bypassPermissions.
PHASE_CONF = {
    "orient": {
        # Orient can read + edit state files, but NOT run commands or create files.
        # disallowed_tools is the ONLY way to enforce this under bypassPermissions.
        "allowed_tools": ["Read", "Glob", "Grep", "Edit"],
        "disallowed_tools": ["Bash", "Write"],
        "hooks": {
            "PreToolUse": [
                HookMatcher(matcher="Edit", hooks=[orient_edit_guard]),
            ],
        },
    },
    "review": {
        "allowed_tools": ["Read", "Glob", "Grep", "Edit", "Bash"],
        "disallowed_tools": [],
        "hooks": {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[safety_guard]),
            ],
        },
    },
    "default": {
        "allowed_tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        "disallowed_tools": [],
        "hooks": {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[safety_guard]),
            ],
        },
    },
}

PHASE_KEYS = {
    "init": "phase_init", "work": "phase_work",
    "review": "phase_review", "orient": "phase_orient",
}


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
        allowed_tools=pc["allowed_tools"],
        max_turns=max_turns,
        cwd=str(project),
        permission_mode="bypassPermissions",
        hooks=pc["hooks"],
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


# ═══════════════════════════════════════════════════════════════
# Dual-Loop Engine
# ═══════════════════════════════════════════════════════════════


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def engine(args):
    """Nested dual-loop: outer OODA (strategic) + inner SDK (tactical)."""
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

    # Copy CLAUDE.md from mode if project doesn't have one
    if not (project / "CLAUDE.md").exists():
        src = mode_dir / conf.get("claude_md", "CLAUDE.md")
        if not src.exists():
            src = SCRIPT_DIR / "CLAUDE.md"
        if src.exists():
            (project / "CLAUDE.md").write_text(src.read_text())

    state_path = project / ".state" / conf.get("state_file", "tasks.json")

    # ── Banner ──
    print(f"\n  {'='*52}")
    print(f"       auto-dev-agentos v{VERSION} (SDK Engine)")
    print(f"    Nested Dual-Loop: OODA x SDK")
    print(f"  {'='*52}\n")
    print(f"  Mode    : {args.mode}")
    print(f"  Project : {project}")
    print(f"  Sessions: max {args.max_sessions}")
    print(f"  Review  : every {args.review_interval} | Orient: every {args.orient_interval}\n")

    if args.dry_run:
        print(f"  [DRY RUN] No agents will be invoked.\n")
        phase = get_phase(state_path, conf)
        done = progress_count(state_path, conf)
        total = done  # approximate
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                # Count all items in the primary array
                for key in ["tasks", "experiments", "findings"]:
                    if key in data:
                        total = len(data[key])
                        break
            except (json.JSONDecodeError, ValueError):
                pass
        print(f"  Phase     : {phase}")
        print(f"  Progress  : {done}/{total} completed")
        print(f"  Entry file: {entry} {'(exists)' if (project / entry).exists() else '(MISSING)'}")
        print(f"  State file: {conf.get('state_file', 'tasks.json')} {'(exists)' if state_path.exists() else '(will be created)'}")

        # Show which prompt would be loaded
        phase_keys_map = {"init": "phase_init", "work": "phase_work", "review": "phase_review", "orient": "phase_orient"}
        prompt_name = conf.get(phase_keys_map.get(phase, ""), phase)
        prompt_file = mode_dir / "prompts" / f"{prompt_name}.md"
        print(f"  Next prompt: {prompt_file.name} {'(exists)' if prompt_file.exists() else '(MISSING)'}")

        # Show tool permissions for this phase
        pc = PHASE_CONF.get(phase, PHASE_CONF["default"])
        print(f"  Tools     : {', '.join(pc['allowed_tools'])}")
        if pc.get("disallowed_tools"):
            print(f"  Blocked   : {', '.join(pc['disallowed_tools'])}")
        return

    session = 0
    no_progress = 0
    total_cost = 0.0

    # ── Main Loop ──────────────────────────────────────────────
    while True:
        session += 1
        if session > args.max_sessions:
            print(f"[{ts()}] Max sessions ({args.max_sessions}). Stopping.")
            break

        phase = get_phase(state_path, conf)
        if phase == "done":
            print(f"[{ts()}] All work complete!")
            break

        # ── OODA Orient (strategic review) ──
        if session > 1 and session % args.orient_interval == 0:
            print(f"\n[{ts()}] == OODA Orient ==")
            r = await run_session(
                project, mode_dir, conf, "orient", f"orient_{session}", 15
            )
            total_cost += r["cost"]
            if r["status"] != "skipped":
                print(f"[{ts()}] Orient: {r['status']} | ${r['cost']:.4f}")
            # Re-check phase — strategist may have changed state
            phase = get_phase(state_path, conf)
            if phase == "done":
                print(f"[{ts()}] Orient determined: complete!")
                break

        # Snapshot for stuck detection
        prev = progress_count(state_path, conf)

        # Run init.sh before work sessions (matches run.sh behavior)
        if phase == "work":
            init_script = project / "init.sh"
            if init_script.exists():
                subprocess.run(
                    ["bash", str(init_script)],
                    cwd=str(project),
                    capture_output=True,
                    timeout=60,
                )

        # ── Tactical Session ──
        print(f"\n[{ts()}] Session #{session} -- {phase} [{args.mode}]")
        r = await run_session(
            project, mode_dir, conf, phase, str(session), args.max_turns
        )
        total_cost += r["cost"]
        print(
            f"[{ts()}] #{session}: {r['status']} | "
            f"${r['cost']:.4f} | {r['turns']} turns | "
            f"total ${total_cost:.4f}"
        )

        if r["complete"]:
            print(f"[{ts()}] Agent confirmed complete!")
            break

        # ── Circuit Breaker ──
        if phase == "work":
            curr = progress_count(state_path, conf)
            if curr <= prev:
                no_progress += 1
                print(f"[{ts()}] No progress ({no_progress}/{args.no_progress_max})")
                if no_progress >= args.no_progress_max:
                    print(f"[{ts()}] Stuck. Stopping.")
                    break
            else:
                no_progress = 0

        # ── Tactical Review ──
        if session >= args.review_interval and session % args.review_interval == 0:
            print(f"\n[{ts()}] == Tactical Review ==")
            r = await run_session(
                project, mode_dir, conf, "review", f"review_{session}", 20
            )
            total_cost += r["cost"]
            print(f"[{ts()}] Review: {r['status']} | ${r['cost']:.4f}")

        await asyncio.sleep(args.pause)

    # ── Summary ──
    print(f"\n[{ts()}] Done. {args.mode} | {session} sessions | ${total_cost:.4f}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    p = argparse.ArgumentParser(
        description=f"auto-dev-agentos v{VERSION} -- SDK Dual-Loop Engine"
    )
    p.add_argument("project_dir", nargs="?", help="Project directory")
    p.add_argument("--mode", default="engineer", help="Execution mode (default: engineer)")
    p.add_argument("--max-sessions", type=int, default=50)
    p.add_argument("--max-turns", type=int, default=50, help="Max LLM turns per session")
    p.add_argument("--review-interval", type=int, default=5)
    p.add_argument("--orient-interval", type=int, default=10, help="Strategic review interval")
    p.add_argument("--no-progress-max", type=int, default=3)
    p.add_argument("--pause", type=int, default=5, help="Seconds between sessions")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen without running agents")
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

    asyncio.run(engine(args))


if __name__ == "__main__":
    main()
