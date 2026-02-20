#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# auto-dev-agentos v3.0 — Universal Autonomous Agent Engine
# Architecture: Mode-agnostic executor + circuit breaker
#   Loads mode-specific prompts from modes/<mode>/prompts/
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION="3.0"

# ── Defaults ─────────────────────────────────────────────────────
MODE="engineer"
MAX_SESSIONS=50
PAUSE_SEC="${PAUSE_SEC:-5}"
REVIEW_INTERVAL="${REVIEW_INTERVAL:-5}"
NO_PROGRESS_MAX="${NO_PROGRESS_MAX:-3}"

# ── CLI Parsing ──────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: ./run.sh [OPTIONS] <project-dir> [max-sessions]

Options:
  --mode <name>    Execution mode (default: engineer)
                   Loads prompts from modes/<name>/prompts/
  --list-modes     List available modes and exit
  -h, --help       Show this help and exit

Environment:
  PAUSE_SEC          Seconds between sessions (default: 5)
  REVIEW_INTERVAL    Run reviewer every N sessions (default: 5)
  NO_PROGRESS_MAX    Max no-progress sessions before abort (default: 3)

Examples:
  ./run.sh my-project
  ./run.sh --mode researcher quant-lab
  ./run.sh --mode engineer my-app 20
EOF
  exit 0
}

list_modes() {
  echo "Available modes:"
  for dir in "$SCRIPT_DIR"/modes/*/; do
    local name
    name="$(basename "$dir")"
    local desc="(no description)"
    if [[ -f "$dir/mode.conf" ]]; then
      desc=$(grep '^description=' "$dir/mode.conf" 2>/dev/null | cut -d= -f2- || echo "(no description)")
    fi
    echo "  $name — $desc"
  done
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)     MODE="$2"; shift 2 ;;
    --list-modes) list_modes ;;
    -h|--help)  usage ;;
    -*)         echo "Unknown option: $1" >&2; exit 1 ;;
    *)          break ;;
  esac
done

PROJECT_DIR="${1:?Usage: ./run.sh [--mode <mode>] <project-dir> [max-sessions]}"
MAX_SESSIONS="${2:-$MAX_SESSIONS}"

# ── Resolve Paths ────────────────────────────────────────────────
MODE_DIR="$SCRIPT_DIR/modes/$MODE"
if [[ ! -d "$MODE_DIR" ]]; then
  echo "ERROR: Mode '$MODE' not found. Available modes:" >&2
  for d in "$SCRIPT_DIR"/modes/*/; do echo "  $(basename "$d")" >&2; done
  exit 1
fi

[[ ! -d "$PROJECT_DIR" ]] && mkdir -p "$PROJECT_DIR"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
mkdir -p "$PROJECT_DIR/.state" "$PROJECT_DIR/logs"

# ── Load Mode Configuration ─────────────────────────────────────
# mode.conf provides mode-specific behavior hooks as key=value pairs:
#   description       — Human-readable mode description
#   entry_file        — Required input file (e.g., spec.md, hypothesis.md)
#   state_file        — Primary state JSON file (e.g., tasks.json, journal.json)
#   pending_query     — jq query that returns count of pending work items
#   progress_query    — jq query that returns count of completed items
#   phases            — Comma-separated phase names (maps to prompt files)
#   phase_detect      — jq expression returning current phase name
#   claude_md         — CLAUDE.md template to copy (relative to mode dir)

load_conf() {
  local key="$1" default="$2"
  if [[ -f "$MODE_DIR/mode.conf" ]]; then
    grep "^${key}=" "$MODE_DIR/mode.conf" 2>/dev/null | head -1 | cut -d= -f2- || echo "$default"
  else
    echo "$default"
  fi
}

ENTRY_FILE=$(load_conf "entry_file" "spec.md")
STATE_FILE=$(load_conf "state_file" "tasks.json")
PENDING_QUERY=$(load_conf "pending_query" '[.tasks[] | select(.status == "pending" or .status == "in_progress")] | length')
PROGRESS_QUERY=$(load_conf "progress_query" '[.tasks[] | select(.status == "done")] | length')
PHASE_INIT=$(load_conf "phase_init" "initializer")
PHASE_WORK=$(load_conf "phase_work" "developer")
PHASE_REVIEW=$(load_conf "phase_review" "reviewer")
CLAUDE_MD=$(load_conf "claude_md" "CLAUDE.md")

# ── Colors & Logging ────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
err() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*" >&2; }

# ── Banner ───────────────────────────────────────────────────────
echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║       auto-dev-agentos v${VERSION}                    ║"
echo "  ║  Universal Autonomous Agent Engine               ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
log "Mode    : ${BOLD}${MODE}${NC}"
log "Project : $PROJECT_DIR"
log "Max     : $MAX_SESSIONS sessions"
log "Review  : every $REVIEW_INTERVAL sessions"
echo ""

# ── Prerequisites ────────────────────────────────────────────────
for cmd in claude jq; do
  if ! command -v "$cmd" &>/dev/null; then
    err "$cmd not found. Required dependency."
    exit 1
  fi
done

# ── Copy CLAUDE.md (mode-specific) ───────────────────────────────
if [[ ! -f "$PROJECT_DIR/CLAUDE.md" ]]; then
  local_claude="$MODE_DIR/$CLAUDE_MD"
  if [[ -f "$local_claude" ]]; then
    cp "$local_claude" "$PROJECT_DIR/CLAUDE.md"
    log "Copied CLAUDE.md (from mode: $MODE)"
  elif [[ -f "$SCRIPT_DIR/CLAUDE.md" ]]; then
    cp "$SCRIPT_DIR/CLAUDE.md" "$PROJECT_DIR/CLAUDE.md"
    log "Copied CLAUDE.md (default)"
  fi
fi

# ── Verify Entry File ───────────────────────────────────────────
if [[ ! -f "$PROJECT_DIR/$ENTRY_FILE" ]]; then
  err "No $ENTRY_FILE in $PROJECT_DIR. Required for --mode $MODE."
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════
# UNIVERSAL ENGINE — Mode-agnostic executor + circuit breaker
# ═══════════════════════════════════════════════════════════════════

SESSION=0
NO_PROGRESS_COUNT=0

# ── Phase Detection ──────────────────────────────────────────────
# Returns: init | work | done
get_phase() {
  if [[ ! -f "$PROJECT_DIR/.state/$STATE_FILE" ]]; then
    echo "init"
    return
  fi
  local pending
  pending=$(jq "$PENDING_QUERY" "$PROJECT_DIR/.state/$STATE_FILE" 2>/dev/null || echo "0")
  if [[ "$pending" -gt 0 ]]; then
    echo "work"
  else
    echo "done"
  fi
}

# ── Progress Snapshot (for circuit breaker) ──────────────────────
snapshot_progress() {
  if [[ -f "$PROJECT_DIR/.state/$STATE_FILE" ]]; then
    jq "$PROGRESS_QUERY" "$PROJECT_DIR/.state/$STATE_FILE" 2>/dev/null || echo "0"
  else
    echo "0"
  fi
}

# ── Run init.sh if present ───────────────────────────────────────
run_init_script() {
  if [[ -f "$PROJECT_DIR/init.sh" ]]; then
    log "Running init.sh..."
    (cd "$PROJECT_DIR" && bash init.sh) >> "$PROJECT_DIR/logs/init.log" 2>&1 || true
  fi
}

# ── Resolve Prompt File for Phase ────────────────────────────────
resolve_prompt() {
  local phase="$1"
  local prompt_name
  case "$phase" in
    init)   prompt_name="$PHASE_INIT" ;;
    work)   prompt_name="$PHASE_WORK" ;;
    review) prompt_name="$PHASE_REVIEW" ;;
    *)      err "Unknown phase: $phase"; return 1 ;;
  esac

  local prompt_file="$MODE_DIR/prompts/${prompt_name}.md"
  if [[ ! -f "$prompt_file" ]]; then
    err "Prompt file not found: $prompt_file"
    return 1
  fi
  echo "$prompt_file"
}

# ── Execute One Session ─────────────────────────────────────────
run_session() {
  local phase="$1" session_id="$2"
  local log_file="$PROJECT_DIR/logs/session_${session_id}.log"
  local prompt_file
  prompt_file="$(resolve_prompt "$phase")" || return 1

  log "Session #${session_id} — ${YELLOW}${phase}${NC} [${MODE}] → $(basename "$prompt_file")"

  # Run init.sh before each work session
  [[ "$phase" == "work" ]] && run_init_script

  # Execute: deliver prompt via stdin (avoids ARG_MAX)
  local result
  if result=$(cd "$PROJECT_DIR" && claude -p \
    --dangerously-skip-permissions \
    --output-format text \
    < "$prompt_file" 2>&1); then
    echo "$result" > "$log_file"
    log "${GREEN}Session $session_id completed${NC}"
  else
    echo "$result" > "$log_file"
    err "Session $session_id failed. See $log_file"
    return 1
  fi

  # Check for COMPLETE signal
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    log "${GREEN}Agent signaled COMPLETE${NC}"
    return 2
  fi
  return 0
}

# ── Review Trigger ───────────────────────────────────────────────
maybe_review() {
  local s="$1"
  if (( s % REVIEW_INTERVAL == 0 && s >= REVIEW_INTERVAL )); then
    local review_prompt
    review_prompt="$(resolve_prompt "review")" || return 0

    log "${YELLOW}Triggering review...${NC}"
    (cd "$PROJECT_DIR" && claude -p \
      --dangerously-skip-permissions \
      --output-format text \
      < "$review_prompt") \
      > "$PROJECT_DIR/logs/review_${s}.log" 2>&1 || true
    log "Review complete → logs/review_${s}.log"
  fi
}

# ── Trap ─────────────────────────────────────────────────────────
trap 'echo ""; log "Interrupted. State preserved in .state/"; exit 0' INT

# ═══════════════════════════════════════════════════════════════════
# MAIN LOOP — Universal executor with circuit breaker
# ═══════════════════════════════════════════════════════════════════
while true; do
  SESSION=$((SESSION + 1))

  # Circuit breaker: max sessions
  if (( SESSION > MAX_SESSIONS )); then
    log "${YELLOW}Reached max sessions ($MAX_SESSIONS). Stopping.${NC}"
    break
  fi

  PHASE="$(get_phase)"
  if [[ "$PHASE" == "done" ]]; then
    log "${GREEN}🎉 All work complete! Project is ready.${NC}"
    break
  fi

  # Snapshot before session (for stuck detection)
  prev_done="$(snapshot_progress)"

  echo ""
  run_ret=0
  run_session "$PHASE" "$SESSION" || run_ret=$?

  # Agent signaled COMPLETE
  if [[ $run_ret -eq 2 ]]; then
    log "${GREEN}🎉 Agent confirmed project complete!${NC}"
    break
  fi

  # Circuit breaker: stuck detection (only during work phase)
  if [[ "$PHASE" == "work" ]]; then
    curr_done="$(snapshot_progress)"
    if [[ "$curr_done" -le "$prev_done" ]]; then
      NO_PROGRESS_COUNT=$((NO_PROGRESS_COUNT + 1))
      log "${YELLOW}No progress detected ($NO_PROGRESS_COUNT/$NO_PROGRESS_MAX)${NC}"
      if (( NO_PROGRESS_COUNT >= NO_PROGRESS_MAX )); then
        err "Stuck for $NO_PROGRESS_MAX consecutive sessions. Stopping."
        break
      fi
    else
      NO_PROGRESS_COUNT=0
    fi
  fi

  maybe_review "$SESSION"

  log "Next session in ${PAUSE_SEC}s..."
  sleep "$PAUSE_SEC"
done

log "Done. Mode: $MODE | Total sessions: $SESSION"
