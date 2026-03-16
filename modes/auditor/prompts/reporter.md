# Reporter Agent

Triggered periodically to synthesize audit findings into a structured report and assess overall audit progress.

## Steps

### 1. Collect Data

```bash
cat standards.md
cat .state/findings.json
cat .state/progress.md
cat CLAUDE.md
git log --oneline -20
```

### 2. Analyze Audit Progress

| Metric | How to compute | Healthy |
|--------|---------------|---------|
| Findings scanned | total entries | Matches initial scan |
| Verified findings | status == "verified" | Documented |
| Dismissed findings | status == "dismissed" | With justification |
| Pending findings | status == "pending" | Decreasing |
| Critical findings | severity == "critical" AND verified | Highlighted |
| Coverage | categories covered vs. standards defined | Complete |

### 3. Generate Audit Report

Create or update `.state/audit_report.md`:

```markdown
# Audit Report — [Project Name]

**Date**: [timestamp]
**Scope**: [from findings.json audit_scope]
**Standards**: [from standards.md]

## Executive Summary

- **Total findings scanned**: [N]
- **Verified issues**: [N] (Critical: [N], High: [N], Medium: [N], Low: [N])
- **Dismissed (false positives)**: [N]
- **Pending review**: [N]

## Critical & High Findings

### F-001: [Title] [CRITICAL]
**Location**: [file:line]
**Evidence**: [summary]
**Impact**: [what could go wrong]
**Recommendation**: [how to fix]

---

## Medium & Low Findings

[Similar format, less detail]

## Dismissed Findings

| ID | Title | Reason for dismissal |
|----|-------|---------------------|
| F-003 | ... | False positive because... |

## Recommendations

1. [Prioritized list of actions]

## Audit Methodology

This audit was conducted using auto-dev-agentos in auditor mode.
Each finding was individually verified with code evidence.
```

### 4. Update Progress

Append to `.state/progress.md`:
```markdown
## 📋 Audit Review — [timestamp]
**Findings analyzed**: [range]
**Progress**: [X verified] | [Y dismissed] | [Z pending]
**Critical issues**: [count and brief list]
```

### 5. Commit

```bash
git add -A
git commit -m "audit: report — [X] verified, [Y] dismissed, [Z] pending"
```
