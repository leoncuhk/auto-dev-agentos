#!/usr/bin/env bash
# auto-dev-agentos v2.0 — Lightweight BMALPH
# Autonomous Development Agent OS
# Architecture: Initializer → Developer (loop) → Reviewer (periodic) → Done
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${1:?Usage: ./run.sh <project-dir> [max-sessions]}"
MAX_SESSIONS="${2:-50}"
PAUSE_SEC="${PAUSE_SEC:-5}"
REVIEW_INTERVAL="${REVIEW_INTERVAL:-5}"
SESSION=0
NO_PROGRESS_COUNT=0
NO_PROGRESS_MAX="${NO_PROGRESS_MAX:-3}"

# Resolve project dir
[[ ! -d "$PROJECT_DIR" ]] && mkdir -p "$PROJECT_DIR"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
mkdir -p "$PROJECT_DIR/.state" "$PROJECT_DIR/logs"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
err() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*" >&2; }

# ── Banner ───────────────────────────────────────────────────────
echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       auto-dev-agentos v2.0                  ║"
echo "  ║  Lightweight BMALPH — Autonomous Dev OS      ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Prerequisites ────────────────────────────────────────────────
for cmd in claude jq; do
  if ! command -v "$cmd" &>/dev/null; then
    err "$cmd not found. Required dependency."
    exit 1
  fi
done

# ── Copy CLAUDE.md if not present ────────────────────────────────
[[ ! -f "$PROJECT_DIR/CLAUDE.md" ]] && cp "$SCRIPT_DIR/CLAUDE.md" "$PROJECT_DIR/CLAUDE.md" && log "Copied CLAUDE.md"

# ── Verify spec.md ───────────────────────────────────────────────
if [[ ! -f "$PROJECT_DIR/spec.md" ]]; then
  err "No spec.md in $PROJECT_DIR. Create one and retry."
  exit 1
fi

log "Project : $PROJECT_DIR"
log "Max     : $MAX_SESSIONS sessions"
log "Review  : every $REVIEW_INTERVAL sessions"
echo ""

# ── Mode detection ───────────────────────────────────────────────
get_mode() {
  if [[ ! -f "$PROJECT_DIR/.state/tasks.json" ]]; then
    echo "init"
    return
  fi
  local pending done_count total
  pending=$(jq '[.tasks[] | select(.status == "pending" or .status == "in_progress")] | length' \
    "$PROJECT_DIR/.state/tasks.json" 2>/dev/null || echo "0")
  if [[ "$pending" -gt 0 ]]; then
    echo "dev"
  else
    echo "done"
  fi
}

# ── Snapshot task state (for stuck detection) ────────────────────
snapshot_tasks() {
  if [[ -f "$PROJECT_DIR/.state/tasks.json" ]]; then
    jq '[.tasks[] | select(.status == "done")] | length' "$PROJECT_DIR/.state/tasks.json" 2>/dev/null || echo "0"
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

# ── Run one session (stdin prompt delivery + output capture) ─────
run_session() {
  local mode="$1" session_id="$2"
  local log_file="$PROJECT_DIR/logs/session_${session_id}.log"
  local prompt_file="$SCRIPT_DIR/prompts/${mode}r.md"
  [[ "$mode" == "init" ]] && prompt_file="$SCRIPT_DIR/prompts/initializer.md"
  [[ "$mode" == "dev" ]]  && prompt_file="$SCRIPT_DIR/prompts/developer.md"

  log "Session #${session_id} — ${YELLOW}${mode}${NC} mode"

  # Run init.sh before each dev session
  [[ "$mode" == "dev" ]] && run_init_script

  # Deliver prompt via stdin (avoids ARG_MAX shell limits)
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

  # Check for COMPLETE signal from agent output
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    log "${GREEN}Agent signaled COMPLETE${NC}"
    return 2  # special exit code = done
  fi
  return 0
}

# ── Review trigger ───────────────────────────────────────────────
maybe_review() {
  local s="$1"
  if (( s % REVIEW_INTERVAL == 0 && s >= REVIEW_INTERVAL )); then
    log "${YELLOW}Triggering review...${NC}"
    (cd "$PROJECT_DIR" && claude -p \
      --dangerously-skip-permissions \
      --output-format text \
      < "$SCRIPT_DIR/prompts/reviewer.md") \
      > "$PROJECT_DIR/logs/review_${s}.log" 2>&1 || true
    log "Review complete → logs/review_${s}.log"
  fi
}

# ── Trap ─────────────────────────────────────────────────────────
trap 'echo ""; log "Interrupted. State preserved in .state/"; exit 0' INT

# ── Main loop ────────────────────────────────────────────────────
while true; do
  SESSION=$((SESSION + 1))

  if (( SESSION > MAX_SESSIONS )); then
    log "${YELLOW}Reached max sessions ($MAX_SESSIONS). Stopping.${NC}"
    break
  fi

  MODE="$(get_mode)"
  if [[ "$MODE" == "done" ]]; then
    log "${GREEN}🎉 All tasks complete! Project is ready.${NC}"
    break
  fi

  # Snapshot before session (for stuck detection)
  prev_done="$(snapshot_tasks)"

  echo ""
  run_ret=0
  run_session "$MODE" "$SESSION" || run_ret=$?

  # Agent signaled COMPLETE
  if [[ $run_ret -eq 2 ]]; then
    log "${GREEN}🎉 Agent confirmed project complete!${NC}"
    break
  fi

  # Stuck detection: no new tasks completed
  if [[ "$MODE" == "dev" ]]; then
    curr_done="$(snapshot_tasks)"
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

log "Done. Total sessions: $SESSION"
