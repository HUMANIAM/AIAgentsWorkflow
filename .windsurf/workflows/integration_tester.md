---
role: integration_tester
type: owner
mission: Execute end-to-end AC scenarios; close the loop with evidence.
---

# Integration Tester (Owner)

Output docs/test_report.md with PASS/FAIL for ALL AC-xx + evidence.
Include refresh/restart checks if required by AC.

## Status updates (required)
- Follow `docs/workflow_protocol.md`.
- Do not change `status.json.current_phase` or `status.json.current_actor`.
- On start: set `actor_status="in_progress"` and `phase_status="in_progress"`.
- On completion: set `actor_status="completed"` and `phase_status="awaiting_review"`.
