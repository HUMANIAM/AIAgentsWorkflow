# State Model

## Principle
Store only what must persist; derive computed flags to avoid drift.

## Stored fields
- profile binding: `active_profile`, `phase_plan`, `current_step_index`
- cursor: `current_phase`, `current_role`
- status: `phase_status`, `role_status`, `review_status`
- realization: `realization_status`, `pending_human_gate_id`, `pending_human_question_id`
- execution mode: `execution_mode`, `workspace_dir`, `workspace_git_initialized`, `active_run_id`
- integration controls: `last_failed_role`, `integration_loop_status`, `role_attempts`
- git evidence: `commit_evidence`
- collaboration: `questions`, `answers`, `governance_gates`
- controls: `review_cycles`, `handoff_packet`
- evidence: `artifacts`, `evidence`
- audit metadata: `charter_version`, `score_run_id`, `timestamps`

## Derived fields
- `is_blocked`
- `phase_ready_to_advance`
- `missing_outputs`
- `pending_required_questions`
- `human_gate_waiting`

## Why this model
Derived blocking avoids contradictory states such as:
- pending required questions while flow advances,
- pending gate while release progresses,
- completed role without required handoff outputs.
