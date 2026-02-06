# Enforce Git Discipline for Agents

This plan addresses the gap between documented Git/CI policy and actual agent behavior - agents currently make large commits directly without following the branch/PR/CI workflow.

---

## Problem

The workflow documentation says agents should:
1. Work on feature branches (`cs/<changeset_id>`)
2. Make small commits per change
3. Create PRs for review
4. Wait for CI to pass before merge

**But in practice**, agents:
- Commit directly to main (bypassing branch protection)
- Make large commits with many changes
- Skip PR creation and CI checks
- Don't follow the ChangeSet pattern

---

## Root Cause

The agent workflow files (`.windsurf/workflows/*.md`) mention "ChangeSets" and "never merge to main" but **lack explicit step-by-step Git commands**. The orchestrator workflow has the Git policy but agents don't have actionable instructions.

---

## Proposed Fix

### Option A: Add Git Steps to Each Agent Workflow (Recommended)

Update each owner workflow (backend.md, devops.md, frontend.md, etc.) with explicit Git section:

```markdown
## Git Workflow (MANDATORY)

Before making changes:
1. Create branch: `git checkout -b cs/CS-<date>-<seq>`
2. Make small, focused commits: `git commit -m "<type>: <description>"`

After completing work:
1. Push branch: `git push -u origin cs/CS-<date>-<seq>`
2. Do NOT create PR - orchestrator handles this
3. Update status.json with actor_status="completed"

Commit message format:
- `feat:` new feature
- `fix:` bug fix
- `chore:` maintenance
- `docs:` documentation
- `test:` tests
```

### Option B: Create a Shared Git Protocol File

Create `docs/git_protocol.md` and reference it from all agent workflows.

### Option C: Enforce via Pre-commit Hooks

Add `.pre-commit-config.yaml` to enforce commit message format and prevent direct pushes to main.

---

## Files to Modify

| File | Change |
|------|--------|
| `.windsurf/workflows/backend.md` | Add Git section |
| `.windsurf/workflows/devops.md` | Add Git section |
| `.windsurf/workflows/frontend.md` | Add Git section |
| `.windsurf/workflows/architect.md` | Add Git section |
| `.windsurf/workflows/system_analyst.md` | Add Git section |
| `docs/git_protocol.md` | New file with shared Git rules |

---

## Implementation Steps

1. Create `docs/git_protocol.md` with detailed Git workflow
2. Update each owner workflow to include Git section referencing the protocol
3. Add ChangeSet ID generation logic (date-based sequence)
4. Test with a sample task to verify agents follow the flow

---

## Questions for User

1. Do you want agents to create PRs themselves, or should only orchestrator create PRs?
2. Should we add pre-commit hooks to enforce commit message format?
3. Do you want to enforce this immediately or test on next task first?
