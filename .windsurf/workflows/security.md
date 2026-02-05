---
role: security
type: owner
mission: Security review with evidence and fixes; produce security report.
---

# Security (Owner)

Output docs/security_report.md with findings, evidence, fixes, verdict.
Record security-related decisions as D-... if needed.

## Status updates (required)
- Follow `docs/workflow_protocol.md`.
- Do not change `status.json.current_phase` or `status.json.current_actor`.
- On start: set `actor_status="in_progress"` and `phase_status="in_progress"`.
- On completion: set `actor_status="completed"` and `phase_status="awaiting_review"`.
