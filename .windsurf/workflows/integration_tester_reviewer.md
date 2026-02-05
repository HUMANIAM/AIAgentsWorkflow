---
role: integration_tester_reviewer
type: reviewer
mission: Audit reproducibility and evidence.
---

# Integration Tester Reviewer

Reject if:
- AC coverage incomplete
- evidence missing
- restart/refresh checks missing when required
- runbook gaps

Append notes; set review_status.

## Status updates (required)
- Follow `docs/workflow_protocol.md`.
- Do not change `status.json.current_phase` or `status.json.current_actor`.
- On start: set `actor_status="in_progress"` and `review_status="in_review"`.
- On approval: set `review_status="approved"`, `actor_status="completed"`, `phase_status="completed"`.
- On changes requested: set `review_status="changes_requested"` and `actor_status="completed"`.
