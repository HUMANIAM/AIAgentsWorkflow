---
role: human_engineer
charter_version: v2.1
profile_scope: [default_fallback_profile, smartbookmarker_realization]
mission: Own intent, approvals, and risk acceptance for the delivery lifecycle.
---

# Human Engineer Charter

## Authority
- Approve or reject idea activation.
- Approve or reject `REQ_FREEZE_APPROVAL` and `RELEASE_APPROVAL` gates.
- Override agent recommendations with rationale.

## Non-Authority
- Must not bypass audit logging of approvals/overrides.
- Must not approve release without evidence review.

## Required Inputs
- Intent/context draft from bot/plugin.
- Acceptance contract and review artifacts.
- Release package (checklist, test/security/eval reports).

## Required Outputs
- Gate decision artifact:
  - `agent_runtime/artifacts/gate_req_freeze.md`
  - `agent_runtime/artifacts/gate_release_approval.md`
- Decision rationale in status gate reason field.

## Quality Gates
- Approval must reference reviewed evidence.
- Rejection must include actionable reason.

## Failure Policy
- If evidence is insufficient, reject gate with explicit remediation request.

## Handoff Packet Requirements
- Include decision (`approved|rejected`), reason, timestamp.

## Definition of Done
- Required human gate decision recorded and traceable.
