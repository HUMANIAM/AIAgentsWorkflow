# Human Control Policy

## Human authority
Human engineer/client can:
- approve or reject governance gates,
- approve idea activation,
- pause or resume flow,
- override agent recommendation with recorded rationale,
- reject release.

## Required human decisions
- Idea activation approval.
- `RELEASE_APPROVAL` gate (always required).
- Optional mid-flow gates listed in `ORCHESTRATOR_MIDFLOW_HUMAN_GATES` (for example `REQ_FREEZE_APPROVAL`).

## Non-bypass policy
No agent or orchestrator path may auto-approve required human gates.

## Override audit
Any override must include:
- reason,
- impacted phase/AC,
- risk acknowledgment,
- timestamp.
