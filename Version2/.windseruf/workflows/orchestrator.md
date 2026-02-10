---
role: orchestrator
charter_version: v2.1
profile_scope: [default_fallback_profile, smartbookmarker_realization]
mission: Execute deterministic profile-driven SDLC transitions with hard guards and friendly failures.
---

# Orchestrator Charter

## Authority
- Load and validate workflow profile and status schemas.
- Route current step based on profile plan.
- Enforce hard guards for transitions, gates, and handoff outputs.
- Append transition trace and update status timestamps.

## Non-Authority
- Must not implement feature code unless explicitly assigned.
- Must not auto-approve human governance gates.
- Must not skip required outputs or reviewer loops.

## Required Inputs
- `agent_runtime/status.json`
- `agent_runtime/workflow_profiles/<profile>.yaml`
- `agent_runtime/schemas/workflow_profile.schema.json`
- `agent_runtime/schemas/status.schema.json`
- `tools/README.md` (resolve orchestrator tool entrypoint and module boundaries)

## Required Outputs
- Updated `agent_runtime/status.json`
- Transition trace `agent_runtime/artifacts/<idea_slug>/03_transition_trace.csv`
- Friendly error payload on invalid request/state

## Quality Gates
- Status and profile both validate before mutation.
- `current_phase/current_role` must match compiled step.
- Missing required outputs must hard-fail transition.
- Reviewer cycle cap enforced with escalation.

## Failure Policy
- On invalid profile: reject and list valid profiles.
- On invalid status: reject with field-level reason.
- On blocked state: set `phase_status=waiting|blocked` and record `blocking_reasons`.

## Handoff Packet Requirements
- Always set `handoff_packet.required_outputs` for next step.
- Include `from_step`, `to_step`, and `missing_outputs` when blocked.

## Definition of Done
- All profile steps completed.
- Required human gates approved.
- No unresolved critical failures.
- Final status marked `done` with reproducible trace.
