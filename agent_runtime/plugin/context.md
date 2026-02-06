---
plugin: steward_ai_zorba_bot
version: 3
owner: client
last_updated: 2026-02-04
---

# Goal (this run)
Build `steward_ai_zorba_bot`: a local Telegram bridge that closes the loop for the SDLC pipeline.

Definition of done:
1) Agents can write questions into `status.json.client_questions[]`.
2) The bridge sends those questions to the client on Telegram.
3) The client replies on Telegram using: `<question_id> = <answer>`
4) The bridge writes answers back into `status.json.client_answers[]` and marks matching questions as answered.
5) Evidence is produced in `docs/comms_bootstrap_report.md` and the integration test report confirms AC-01.

# What the bridge must do
- Watch `status.json` (polling is fine; keep it simple).
- For each question where `delivery_status=pending`:
  - send a Telegram message to the client
  - set `delivery_status=sent`, set `delivered_at`
- For each Telegram reply that matches `<question_id> = <answer>`:
  - append to `status.json.client_answers[]`:
    - question_id
    - answer
    - source="telegram"
    - answered_at timestamp
  - mark the corresponding question:
    - `is_answered=true`, `answered_at`, `answered_by="client"`
- Must be safe: only accept replies from allowed user IDs.