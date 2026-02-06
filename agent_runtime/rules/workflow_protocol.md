---
doc: workflow_protocol
version: 1
owner: orchestrator
purpose: "Define the unambiguous status.json state machine and how agents/orchestrator coordinate."
last_updated: 2026-02-05
---

# Workflow Protocol (status.json is truth)

This repo uses `status.json` as the **single source of truth** for SDLC workflow state. The orchestrator must advance the workflow by **triggering the correct agent at the correct time** and recording each transition in `status_history.csv`.

## Canonical phases (strict order)
0) `bootstrap_comms` — owner: `devops`, reviewer: `devops_reviewer`  
1) `requirements` — owner: `system_analyst`, reviewer: `system_analyst_reviewer`  
2) `architecture` — owner: `architect`, reviewer: `architect_reviewer`  
3) `devops` — owner: `devops`, reviewer: `devops_reviewer`  
4) `backend` — owner: `backend`, reviewer: `backend_reviewer`  
5) `backend_testing` — owner: `backend_tester`, reviewer: `backend_tester_reviewer`  
6) `frontend` — owner: `frontend`, reviewer: `frontend_reviewer`  
7) `frontend_testing` — owner: `frontend_tester`, reviewer: `frontend_tester_reviewer`  
8) `integration_testing` — owner: `integration_tester`, reviewer: `integration_tester_reviewer`  
9) `security` — owner: `security`, reviewer: `security_reviewer`  
10) `client_acceptance` — owner: `client` (no reviewer)  
11) `done` — owner: `orchestrator` (terminal)

## status.json fields (contract)

### Core workflow cursor
- `current_phase` (string): one of the canonical phases above.
- `current_actor` (string): the role expected to act **now**.

### State flags (single-phase semantics)
These fields describe the **current phase only**:
- `phase_status` (string): `not_started | in_progress | awaiting_review | completed`
- `actor_status` (string): `not_started | in_progress | completed`
- `review_status` (string): `not_started | in_review | approved | changes_requested`

### Orchestrator-owned vs agent-owned fields
To prevent deadlocks and conflicting updates:
- **Orchestrator owns**: `current_phase`, `current_actor`, phase transitions, and `status_history.csv` appends.
- **Owners/reviewers own**: producing required artifacts for their role and updating `actor_status`/`review_status` for the active phase.
- **Never** have non-orchestrator agents advance `current_phase`.

## How the orchestrator triggers agents (required)

When a phase starts, orchestrator sets:
- `current_phase = <phase>`
- `current_actor = <phase owner role>`
- `phase_status = "in_progress"`
- `actor_status = "not_started"`
- `review_status = "not_started"`

Then the orchestrator must **invoke the owner agent** (e.g., via Windsurf workflow `/system_analyst`).

When the owner completes, the owner agent sets:
- `actor_status = "completed"`
- `phase_status = "awaiting_review"`

Then the orchestrator triggers the reviewer:
- `current_actor = <phase reviewer role>`
- `actor_status = "not_started"`
- `review_status = "in_review"`

When the reviewer finishes, the reviewer sets one of:
- Approval:
  - `review_status = "approved"`
  - `actor_status = "completed"`
  - `phase_status = "completed"`
- Changes requested:
  - `review_status = "changes_requested"`
  - `actor_status = "completed"`
  - keep `phase_status = "in_progress"`

Orchestrator then:
- If approved: advances to next phase owner.
- If changes requested: returns to the same phase owner and starts a review loop.

## History logging (status_history.csv)
`status_history.csv` is append-only. Each row records a transition:

Header (7 columns):
`timestamp,from_phase,from_phase_status,from_actor,to_phase,to_actor,to_phase_status`

Rules:
- Append a row whenever orchestrator changes `current_phase` or `current_actor`.
- Use ISO timestamps.
- Keep rows small and machine-parsable (no free-form commas unless properly CSV-quoted).

## Common deadlocks and self-heal rules
- **Phase completed but gates pending**: reconcile `gates` to reflect completion (or remove stale gates).
- **Owner finished but reviewer never triggered**: orchestrator must switch `current_actor` to reviewer and set `review_status="in_review"`.
- **Reviewer approved but phase not advanced**: orchestrator must advance to next phase.
- **Multiple pollers (Telegram)**: only one process should call `getUpdates` at a time (409 Conflict).

