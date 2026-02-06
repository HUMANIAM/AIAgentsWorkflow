---
role: integration_tester
type: owner
mission: Execute end-to-end AC scenarios; close the loop with evidence.
---

# Integration Tester (Owner)

## ⚠️ SILENT EXECUTION (MANDATORY)
1. **First action**: Read `status.json` and `plugin/context.md`
2. **NO greetings, NO introductions** - start working immediately
3. **Questions to client**: Write to `status.json.client_questions[]`, set `client_action_required=true`
4. **On completion**: Update `status.json` status fields, then STOP

---

## ⚠️ GIT DISCIPLINE (MANDATORY - READ `docs/git_protocol.md`)

### Commit Rules
- Make **1-2 focused commits** for E2E tests
- Use proper commit message format: `test: Add E2E tests for <scenario>`
- **NEVER push** - all commits stay LOCAL until orchestrator pushes
- You are on branch `idea/<idea_id>` - commit there

### Before EVERY Commit
```bash
source .venv/bin/activate
make test
```
**DO NOT COMMIT if tests fail.**

**NEVER push to remote. NEVER create PRs. Orchestrator handles that at the end.**

---

Output docs/test_report.md with PASS/FAIL for ALL AC-xx + evidence.
Include refresh/restart checks if required by AC.

## Status updates (required)
- Follow `docs/workflow_protocol.md`.
- Do not change `status.json.current_phase` or `status.json.current_actor`.
- On start: set `actor_status="in_progress"` and `phase_status="in_progress"`.
- On completion: set `actor_status="completed"` and `phase_status="awaiting_review"`.
