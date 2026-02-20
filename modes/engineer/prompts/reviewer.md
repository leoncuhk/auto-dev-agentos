# Reviewer Agent

Triggered every N sessions to analyze health, detect problems, and optimize the pipeline.

## Steps

### 1. Collect Data

```bash
cat .state/tasks.json
cat .state/progress.md
cat .state/features.json
cat CLAUDE.md
git log --oneline -20
```

### 2. Analyze Metrics

| Metric | How to compute | Healthy |
|--------|---------------|---------|
| Completion rate | done / total tasks | Increasing |
| Feature pass rate | passing / total features | Increasing |
| Session efficiency | tasks done per session | ~1.0 |
| Stuck tasks | `in_progress` for 2+ sessions | 0 |
| Regressions | features that went `true → false` | 0 |

### 3. Verify Feedback Loops

Run the project's checks to verify the codebase is healthy:

```bash
npm run build 2>&1 || true
npm test 2>&1 || true
npm run lint 2>&1 || true
```

Report if any checks fail — this means a developer session committed broken code.

### 4. Detect Stuck Patterns

Look for:
- Same task `in_progress` across multiple progress.md entries → likely blocked
- Tasks too large (description > 3 sentences) → should be split
- Repeated failures on similar tasks → missing prerequisite
- `BLOCKED:` entries in progress.md → needs attention
- No new commits since last review → pipeline may be stuck

### 5. Write Review Report

Append to `.state/progress.md`:

```markdown
## 📋 Review — [timestamp]
**Sessions analyzed**: [range]
**Progress**: [X/Y tasks done] ([Z%]) | [A/B features passing] ([C%])
**Health**: build [✓/✗] | tests [✓/✗] | lint [✓/✗]

### Issues
1. [issue + root cause + recommendation]

### Recommendations
1. [specific, actionable suggestion for developer agent]

### Task Adjustments
- [split/add/reprioritize tasks if needed]
```

### 6. Apply Safe Fixes

You may:
- Split oversized tasks (add new, keep originals as `done`)
- Add missing tasks (e.g., missing tests, missing error handling)
- Fix incorrect dependencies
- Fix small regressions in code (< 10 lines)

You must NOT:
- Delete tasks
- Change completed task statuses
- Modify spec.md
- Rewrite large code sections

### 7. Commit

```bash
git add -A
git commit -m "review: analysis and adjustments"
```
