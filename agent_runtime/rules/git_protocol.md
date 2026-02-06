---
doc: git_protocol
version: 1
owner: orchestrator
purpose: "Enforce Git discipline across all agents - branch first, small commits, local CI, PR last"
last_updated: 2026-02-06
---

# Git Protocol (ALL AGENTS MUST FOLLOW)

## ⚠️ CRITICAL RULES (NON-NEGOTIABLE)

1. **NEVER push directly to main** - all work happens on idea branches
2. **NEVER create PRs** - only orchestrator creates PRs at the end
3. **ALL commits are LOCAL** until orchestrator pushes
4. **RUN TESTS before committing** - use `.venv` for local testing

---

## Branch Naming

```
idea/<idea_id>
Example: idea/internet_browsing_attention_sa
```

Orchestrator creates this branch at flow start. All agents commit to it.

---

## Commit Message Format

```
<type>: <short description>

Types:
- feat:     New feature or functionality
- fix:      Bug fix
- docs:     Documentation only
- test:     Adding or updating tests
- refactor: Code change that neither fixes a bug nor adds a feature
- style:    Formatting, missing semicolons, etc.
- chore:    Maintenance tasks
- security: Security-related changes
```

Examples:
- `feat: Add user authentication endpoint`
- `docs: Add requirements for attention saver`
- `test: Add unit tests for user model`
- `security: Add audit report for idea X`

---

## How to Commit (Step by Step)

```bash
# 1. Check you're on the right branch
git branch  # Should show idea/<idea_id>

# 2. Stage your changes
git add <files>  # Or: git add -A for all

# 3. Commit with proper message
git commit -m "<type>: <description>"

# 4. DO NOT PUSH - orchestrator handles this
```

---

## Commit Discipline by Role

| Role | Commit Style | Why |
|------|--------------|-----|
| System Analyst | 1-2 commits | Docs only, single intent |
| Architect | 1-2 commits | Architecture docs only |
| Backend | Multiple small commits | Implementation needs traceability |
| Frontend | Multiple small commits | Implementation needs traceability |
| Backend Tester | 1-3 commits | Tests per component |
| Frontend Tester | 1-3 commits | Tests per component |
| Integration Tester | 1-2 commits | E2E tests |
| Security | 1 commit | Audit report |
| DevOps | 1-3 commits | CI/tooling setup |

---

## Local Testing (MANDATORY)

Before EVERY commit, run relevant tests:

```bash
# Activate virtual environment
source .venv/bin/activate

# Backend agents
pytest steward_ai_zorba_bot/tests/ -v

# Or use Makefile
make test
```

**DO NOT COMMIT if tests fail.**

---

## Project Structure Per Idea

All idea-related artifacts go in:

```
steward_ai_zorba_bot/apps/<idea_name>/
├── docs/           # Idea-specific documentation
├── tests/          # Idea-specific tests
├── src/            # Implementation code
└── README.md       # Idea overview
```

---

## What Agents Must NOT Do

❌ Push to remote  
❌ Create PRs  
❌ Merge branches  
❌ Commit without testing  
❌ Make large monolithic commits  
❌ Commit unrelated changes together  

---

## What Agents MUST Do

✅ Verify you're on the idea branch: `git branch`  
✅ Commit to the idea branch (local)  
✅ Use proper commit message format  
✅ Run tests before committing  
✅ Keep commits small and focused  
✅ Update status.json when done  

---

## End of Flow (Orchestrator Only)

Only orchestrator performs these steps after all agents complete:

```bash
# 1. Run full CI locally
source .venv/bin/activate
make check && make test

# 2. If CI passes, create PR and push
gh pr create --base main --head idea/<id> --title "Idea: <headline>" --body "..."
git push origin idea/<id>

# 3. Notify client via bot
# Bot sends: "Hi! We finished implementing idea X"
```
