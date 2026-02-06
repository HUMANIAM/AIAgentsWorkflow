---
doc: structure_rules
version: 2
owner: architect
purpose: "Prevent duplication and keep folder structure clean."
last_updated: 2026-02-03
---

# Structure Rules

## Hard rules
1) Do not create new top-level folders without a Decision (D-...) and reviewer approval.
2) Prefer extending existing modules over creating new ones.
3) One source of truth for each topic:
   - Acceptance criteria: docs/acceptance_contract.md
   - Architecture: docs/architecture.md
   - Decisions: docs/decisions.md
   - Run/reset/verify: docs/runbook.md
   - History: docs/change_log.md + status_history.csv

## Refactor policy
- No drive-by refactors inside feature ChangeSets.
- If refactor is needed, isolate it as its own ChangeSet and justify via D-...

## Canonical backend layout (FastAPI pilot)
DevOps + Backend must converge to ONE clean layout and document it here (do not fork layouts).

Suggested baseline:
- backend/app/main.py
- backend/app/api/...
- backend/app/core/...
- backend/app/db/...
- backend/tests/...

This is a suggestion; if you choose another layout, record D-... and update this section.
