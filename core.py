"""
auto-dev-agentos — Pure utility functions.

Shared by run.py (SDK engine) and tests. No SDK dependency.
"""

import json
import re
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
