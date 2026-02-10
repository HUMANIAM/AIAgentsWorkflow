# Phase Model

## Flow source
Phase and role sequence is profile-driven:
- `agent_runtime/workflow_profiles/*.yaml`
- validated by `agent_runtime/schemas/workflow_profile.schema.json`

## `v1_parity_bot` phases
1. requirements
2. architecture
3. implementation
4. verification
5. readiness
6. release

## Phase outputs
- Requirements: `acceptance_contract.md`, `review_requirements.md`
- Architecture: `architecture.md`, `decision_record.md`, `review_architecture.md`
- Implementation: `runbook.md`, `pipeline_notes.md`, `backend_notes.md`, `frontend_notes.md`, `change_log.md`, `review_implementation.md`
- Verification: `test_report.md`, `security_report.md`, `ai_eval_report.md`, `role_scoreboard.json`, `benchmark_results.md`
- Readiness: `runbook.md`, `release_checklist.md`, docs updates, `review_release.md`
- Release: gate approval artifact + final verdict package

## Mandatory human checkpoints
- Checkpoint A: Requirements freeze approval.
- Checkpoint B: Release approval.

Only these checkpoints use governance gates.

## Reviewer phases
- Requirements: Requirements Reviewer
- Architecture: Architecture Reviewer
- Implementation: Implementation Reviewer
- Readiness: Release Reviewer
