# Revised Git & Project Structure Workflow

This plan restructures how agents work with Git: branch first, all commits local, CI check, then PR+push at the end with bot notification.

---

## New Workflow Overview

```
1. /orchestrator or bot "implement idea X"
       ↓
2. Orchestrator creates LOCAL branch: idea/<idea_id>
       ↓
3. All agents commit to this branch (local only)
       ↓
4. Flow completes → Orchestrator runs CI locally in .venv
       ↓
5. If CI passes → Create PR + Push → Bot notifies client
```

---

## Key Changes

### 1. Branch First, PR Last
- Orchestrator creates LOCAL branch at flow start: `idea/<idea_id>`
- All agents commit to this branch locally
- NO push until entire flow completes
- At the end: run CI locally → if pass → create PR + push
- Bot sends: "Hi! We finished implementing idea X"

### 2. Project Structure Per Idea
```
steward_ai_zorba_bot/apps/
├── telegram/           # existing bot app
├── <idea_name>/        # NEW: one folder per idea
│   ├── docs/           # idea-specific docs
│   ├── tests/          # idea-specific tests
│   ├── src/            # idea implementation
│   └── README.md       # idea overview
```

### 3. Commit Discipline by Role

| Role | Commit Style | Example |
|------|--------------|---------|
| System Analyst | Single commit | `docs: Add requirements for <idea>` |
| Architect | Single commit | `docs: Add architecture for <idea>` |
| Backend | Small focused commits | `feat: Add user model`, `feat: Add API endpoint` |
| Frontend | Small focused commits | `feat: Add login component`, `style: Add CSS` |
| Testers | Small commits per test | `test: Add unit tests for user model` |
| Security | Single commit | `security: Add audit report for <idea>` |

### 4. Local Testing Before Commit
- Agents run tests in `.venv` before committing
- DevOps/Backend: `pytest steward_ai_zorba_bot/tests/`
- Frontend: relevant frontend tests
- No commit if tests fail

### 5. Final Steps (Orchestrator)
1. Generate client report
2. Run full CI locally: `make check && make test`
3. Push branch to remote
4. Bot sends Telegram message: "Hi! We finished implementing idea X"

---

## Files to Update

| File | Change |
|------|--------|
| `.windsurf/workflows/orchestrator.md` | Add branch creation on flow start, final push logic |
| `.windsurf/workflows/backend.md` | Add commit discipline, local test requirement |
| `.windsurf/workflows/devops.md` | Add local test requirement |
| `.windsurf/workflows/frontend.md` | Add commit discipline |
| `steward_ai_zorba_bot/apps/telegram/app.py` | Add "idea complete" notification |
| `docs/git_protocol.md` | New file with detailed commit guidelines |

---

## Flow Diagram

```
/orchestrator (or bot: "implement idea X")
       ↓
Orchestrator: git checkout -b idea/<id>   ← LOCAL branch created
       ↓
System Analyst → commit docs (local)
       ↓
Architect → commit architecture (local)
       ↓
Backend → multiple small commits (run pytest in .venv)
       ↓
Backend Tester → commit tests (local)
       ↓
Frontend → multiple small commits (local)
       ↓
Frontend Tester → commit tests (local)
       ↓
Integration Tester → commit tests (local)
       ↓
Security → commit audit (local)
       ↓
Orchestrator: generate client_report.md
       ↓
Orchestrator: source .venv/bin/activate && make check && make test
       ↓
If CI passes:
  - gh pr create --base main --head idea/<id>
  - git push origin idea/<id>
       ↓
Bot sends Telegram: "Hi! We finished implementing idea X"
```

---

## Summary

| Step | Actor | Action |
|------|-------|--------|
| Start | Orchestrator | Create LOCAL branch `idea/<id>` |
| Middle | All agents | Commit locally, run tests in `.venv` |
| End | Orchestrator | Run CI locally, create PR, push, notify |

---

## Confirm to Proceed?

If this matches your intent, I'll update the workflow files. accordingly.
