"""
auto-dev-agentos — Pure utility functions.

Shared by run.py (SDK engine) and tests. No SDK dependency.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load_conf(mode_dir: Path) -> dict:
    """Load mode.conf as a dict."""
    conf = {}
    conf_file = mode_dir / "mode.conf"
    if conf_file.exists():
        for line in conf_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip()
    return conf


def count_by_status(data: dict, jq_query: str) -> int:
    """Evaluate jq-style count queries in pure Python.

    Handles: [.array[] | select(.status == "val" or .status == "val2")] | length
    Limitation: only matches .status field comparisons. Queries filtering on
    other fields (e.g. .type == "x") will mis-match — use explicit Python
    query functions for complex modes instead of jq strings.
    """
    m = re.search(r"\.(\w+)\[\]", jq_query)
    if not m:
        return 0
    items = data.get(m.group(1), [])
    statuses = set(re.findall(r"\.status\s*==\s*\"([^\"]+)\"", jq_query))
    if not statuses:
        statuses = set(re.findall(r'"([^"]+)"', jq_query))
    return sum(1 for item in items if item.get("status") in statuses)


def get_phase(state_path: Path, conf: dict) -> str:
    """Determine current phase: init | work | done."""
    if not state_path.exists():
        return "init"
    try:
        data = json.loads(state_path.read_text())
    except (json.JSONDecodeError, ValueError):
        return "init"

    pending_q = conf.get(
        "pending_query",
        '[.tasks[] | select(.status == "pending" or .status == "in_progress")] | length',
    )
    if count_by_status(data, pending_q) > 0:
        return "work"

    best = data.get("best_metric", 0)
    target = data.get("target_metric", 0)
    if target and best >= target:
        return "done"
    if target and best < target:
        return "init"

    return "done"


def progress_count(state_path: Path, conf: dict) -> int:
    """Count completed items (for circuit breaker)."""
    if not state_path.exists():
        return 0
    try:
        data = json.loads(state_path.read_text())
    except (json.JSONDecodeError, ValueError):
        return 0
    progress_q = conf.get(
        "progress_query",
        '[.tasks[] | select(.status == "done")] | length',
    )
    return count_by_status(data, progress_q)


# --- New functions ---

_SCHEMAS = {
    "engineer": ("tasks", {"pending", "in_progress", "done", "blocked"}),
    "researcher": ("experiments", {"pending", "planned", "running", "accepted", "rejected", "error"}),
    "auditor": ("findings", {"pending", "in_progress", "verified", "dismissed"}),
}


def validate_state(data: dict, mode: str) -> tuple:
    """Validate state data against mode schema. Returns (valid, errors)."""
    errors = []
    if not isinstance(data, dict):
        return False, ["state must be a dict"]
    schema = _SCHEMAS.get(mode)
    if not schema:
        return True, []
    array_key, valid_statuses = schema
    if array_key not in data:
        return False, [f"missing required key: {array_key}"]
    items = data[array_key]
    if not isinstance(items, list):
        return False, [f"{array_key} must be an array"]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{array_key}[{i}]: must be an object")
            continue
        if "id" not in item:
            errors.append(f"{array_key}[{i}]: missing 'id'")
        if "status" not in item:
            errors.append(f"{array_key}[{i}]: missing 'status'")
        elif item["status"] not in valid_statuses:
            errors.append(f"{array_key}[{i}]: invalid status '{item['status']}'")
    return (len(errors) == 0), errors


def parse_metric(output: str):
    """Extract metric from output. Looks for [Metric] <name>: <float>."""
    m = re.search(r"\[Metric\]\s+[^:]+:\s*([0-9]*\.?[0-9]+)", output)
    return float(m.group(1)) if m else None


def run_verify_command(project_dir: str, command: str, timeout: int = 60) -> dict:
    """Run a verification command and return structured result."""
    try:
        result = subprocess.run(
            command, shell=True, cwd=project_dir,
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "metric": parse_metric(result.stdout),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": "timeout", "metric": None}
    except Exception as e:
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e), "metric": None}


def safe_read_state(state_path: Path) -> tuple:
    """Read state file safely. Returns (data, error_message)."""
    if not state_path.exists():
        return None, "file does not exist"
    raw = state_path.read_text()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = state_path.with_name(f"backup_{ts}_{state_path.name}")
        shutil.copy2(state_path, backup)
        return None, f"invalid JSON (backup: {backup.name}): {e}"
    if not isinstance(data, dict):
        return None, "state must be a dict"
    return data, None


def safe_write_state(state_path: Path, data: dict, mode: str) -> tuple:
    """Write state with validation and atomic rename. Returns (success, error)."""
    valid, errors = validate_state(data, mode)
    if not valid:
        return False, "; ".join(errors)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = state_path.with_name(f"backup_{ts}_{state_path.name}")
        shutil.copy2(state_path, backup)
    tmp_path = state_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(str(tmp_path), str(state_path))
    return True, None
