# Agent Git & CI Workflow Explanation

This document explains how agents in the SDLC pipeline interact with Git, CI, and commit their work.

## Overview

The workflow uses `status.json` as the single source of truth. Agents don't directly push to `main` - they work on feature branches and the orchestrator manages merges after CI passes.

---

## Key Roles

| Role | Git Permissions | CI Responsibility |
|------|-----------------|-------------------|
| **Orchestrator** | Merges PRs to main | Waits for CI, fixes failures |
| **Owners** (backend, frontend, etc.) | Push to feature branches | Write code, run local tests |
| **Reviewers** | Review PRs | Approve or request changes |

---

## Git Workflow

### 1. Branch Naming Convention
```
cs/<changeset_id>
Example: cs/CS-20260204-001
```

### 2. Agent Commit Flow 
1. **Owner agent** creates a feature branch
2. Makes changes in small, logical commits
3. Pushes to the branch (NOT main)
4. Updates `status.json.actor_status = "completed"`

### 3. PR Creation (Orchestrator)
```bash
gh pr create --base main --head cs/CS-xxx --title "CS-xxx: <intent>" --body "<body>"
```

### 4. CI Gate (Mandatory)
After every push, orchestrator:
1. Ensures PR exists
2. Waits for CI: `gh pr checks --watch --fail-fast`
3. If CI fails: fix → commit → push → repeat
4. Merge only when CI passes

---

## CI Pipeline (`.github/workflows/backend-ci.yml`)

The CI runs on every PR and push to main:

| Step | Tool | Purpose |
|------|------|---------|
| Lint | `ruff check .` | Code quality |
| Format | `black --check` | Style consistency |
| Type check | `mypy` | Type safety |
| Security | `bandit` | Vulnerability scan |
| Tests | `pytest` | Unit tests |
| Validate | `orchestrator.py validate` | status.json integrity |

---

## How Agents Update Status

### Owner Agent (e.g., `/backend`)
```json
// On start:
"actor_status": "in_progress",
"phase_status": "in_progress"

// On completion:
"actor_status": "completed",
"phase_status": "awaiting_review"
```

### Reviewer Agent (e.g., `/backend_reviewer`)
```json
// On approval:
"review_status": "approved",
"actor_status": "completed",
"phase_status": "completed"

// On changes requested:
"review_status": "changes_requested"
```

---

## Orchestrator Merge Rules

1. **Never merge without CI passing**
2. **Only orchestrator merges** - agents push branches only
3. **PR body must include**: Intent, AC-xx references, D-xx decisions, evidence
4. **After merge**: Delete branch, advance to next phase

---

## Current Implementation Notes

- Branch protection on `main` requires PRs
- Required status check: `backend-test` (CI job)
- Agents communicate via `status.json`, not direct chat
- History logged in `status_history.csv`

---

## Commands Reference

```bash
# Create PR
gh pr create --base main --head <branch> --title "<title>" --body "<body>"

# Check CI status
gh pr checks --fail-fast

# Wait for CI (blocking)
gh pr checks --watch --fail-fast

# View failed logs
gh run list --limit 10
gh run view <run-id> --log-failed

# Merge (orchestrator only)
gh pr merge --merge --delete-branch
```
