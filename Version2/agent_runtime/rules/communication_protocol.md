# Communication Protocol

## Data model
- `questions[]`: each with `id`, `from_role`, `to_human`, `required`, `status`, `created_at`.
- `answers[]`: each with `question_id`, `answer`, `source`, `answered_at`.

Question status values:
- `pending_delivery`
- `delivered`
- `answered`
- `closed`

## Blocking computation
Workflow is blocked when any `questions[]` item satisfies all:
- `required=true`
- `status` is not `answered` or `closed`
- no valid answer entry in `answers[]`

Additionally, workflow blocks when the current step requires a governance gate that is `pending` or `rejected`.

## Bot responsibilities
- Deliver pending questions.
- Record answers mapped by `question_id`.
- Update question status.
- For governance gate questions (`Q-GATE-*`), enforce strict reply mapping:
  - approve: `approve|approved|yes|1`
  - reject: `reject|rejected|no|2`
- On approved gate answer, resume orchestrator autonomous run.

## Orchestrator responsibilities
- Read computed blocking state.
- Pause/resume flow accordingly.
- Never directly fabricate answers.
- Never infer human approvals.

## Governance vs normal questions
- Normal clarification uses `questions[]` and `answers[]` only.
- Governance approvals use `governance_gates[]` plus gate questions (`kind=governance_gate`) for Telegram wakeup.
