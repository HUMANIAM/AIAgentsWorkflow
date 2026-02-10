# Workflow Protocol (Version2)

## Single source of truth
`agent_runtime/status.json` is authoritative for runtime state.

## Canonical sequence source
Role and phase sequencing is defined by workflow profile YAML:
- `agent_runtime/workflow_profiles/*.yaml`
- validated by `agent_runtime/schemas/workflow_profile.schema.json`

Do not duplicate sequence logic in role playbooks.

## Execution modes
- `simulation`: orchestrator impersonates roles and generates deterministic workflow artifacts.
- `realization`: orchestrator still controls transitions, but role work is delegated to the idea-local workspace adapter under `Version2/implementations/<idea_id>/adapter/role_adapter.py`.

## Invocation
- `/orchestrator @<profile_name>`
- Example: `/orchestrator @default_fallback_profile`
- Agent trigger command for autonomous realization:
  - `/orchestrator` via `Version2/tools/src/orchestrator/main.py trigger '/orchestrator'`

## Tool discovery
- Tool entrypoints are resolved from `Version2/tools/README.md`.
- Do not hardcode Version2 tool script paths in agents/clients.

## Orchestrator code structure
- `tools/src/orchestrator/main.py` handles CLI parsing and command routing.
- `tools/src/orchestrator/state_machine.py` is the only transition authority.
- `tools/src/orchestrator/git_protocol.py` enforces commit/governance for realization runs.
- Keep business/project implementation logic outside the generic transition engine.

## Required status fields
- `active_profile`
- `phase_plan`
- `current_step_index`
- `current_phase`
- `current_role`
- `phase_status`
- `role_status`
- `review_status`
- `realization_status`
- `pending_human_gate_id`
- `pending_human_question_id`
- `execution_mode`
- `workspace_dir`
- `workspace_git_initialized`
- `active_run_id`
- `last_failed_role`
- `integration_loop_status`
- `commit_evidence`
- `role_attempts`
- `questions`
- `answers`
- `governance_gates`
- `review_cycles`
- `blocking_reasons`
- `handoff_packet`
- `artifacts`
- `evidence`
- `charter_version`
- `score_run_id`
- `timestamps`

## Execution context fields
When an idea is executed, status should expose:
- `active_idea_id`
- `active_idea_headline`
- `active_idea` object (id/headline/owner/context/profile/timestamp)

## Artifact isolation
- Runtime artifacts and trace files are written under:
  - `agent_runtime/artifacts/<idea_headline_slug>/`
- This directory is derived from `active_idea_headline` (fallback `active_idea_id`).
- Do not write new run artifacts to flat `agent_runtime/artifacts/*`.

## Human gate policy
- `RELEASE_APPROVAL` is always human-required.
- Mid-flow human-required gates come from `ORCHESTRATOR_MIDFLOW_HUMAN_GATES` in `.env`.
- For human-required gates, orchestrator writes approval questions to `questions[]` (`status=pending_delivery`).
- Bot maps client replies strictly:
  - approve: `approve|approved|yes|1`
  - reject: `reject|rejected|no|2`
- Approved gate resumes orchestrator run; rejected gate leaves workflow blocked.

## Realization mode
- `execution_mode=realization` requires workspace bootstrap under:
  - `Version2/implementations/<idea_id>/`
- Orchestrator enforces git protocol per role step.
- Every non-gate step must produce a role-scoped commit.
- Commit evidence is recorded in `10_commit_ledger.md`.

## Hard-guard transition rules
1. Reject invalid profile names with a friendly list of valid profiles.
2. Reject invalid state shape against status schema.
3. Reject illegal transition if `current_phase/current_role` does not match the compiled step.
4. Reject step completion if required outputs are missing from artifacts.
5. Reviewer `changes_requested` routes to producer role and increments `review_cycles.<phase>`.
6. If `review_cycles.<phase>` exceeds configured max, pause and require human decision.
7. Gate steps in human-required set require explicit approval in `governance_gates`.
8. Non-human gate steps can be auto-approved with explicit reason for deterministic autonomous runs.
9. Blocking state must be computed from unanswered required questions, pending gate decisions, and unresolved critical failures.

## Completion conditions
Flow may reach done only when:
- all profile steps complete,
- required gates approved,
- required evidence present,
- no unresolved critical failures.

## Friendly failure UX
On any rejection, return:
- clear reason,
- offending field/step,
- concrete fix hint,
- valid options where applicable.
