---
role: frontend
type: owner
mission: Implement UI exposing stable AC oracles; small ChangeSets with evidence.
---

# Frontend (Owner)

Rules:
- UI must make AC oracles observable and stable.
- Update docs/change_log.md + docs/frontend_notes.md with evidence.
- Never merge to main; orchestrator merges after approvals + CI green.

## Status updates (required)
- Follow `docs/workflow_protocol.md`.
- Do not change `status.json.current_phase` or `status.json.current_actor`.
- On start: set `actor_status="in_progress"` and `phase_status="in_progress"`.
- On completion: set `actor_status="completed"` and `phase_status="awaiting_review"`.
