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

# Comms fallback (never block workflow)
If Telegram is not ready or token is missing:
- Set `status.json.comms.state = "fallback_only"`
- Client answers by editing `status.json.client_answers[]` with `source="status_file"`
- Workflow continues.

# Repo constraints (do not violate)
- Language: Python
- Runtime: Linux local machine
- Keep it minimal: no server hosting required
- Secrets must NEVER be committed

# Where secrets live (already set by client)
- `steward_ai_zorba_bot/.env` contains:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ALLOWED_USER_IDS
  - (optional) TELEGRAM_DEFAULT_CHAT_ID
- The bridge must load env from that file (or accept env vars).

# GitHub policy (must comply)
- No direct pushes to `main`. PR only.
- Required status checks must pass before merge:
  - `backend-test`
- Orchestrator merges PRs only after:
  1) CI green
  2) required reviewer approvals
  3) client ACK (when requested)

# ChangeSet policy (strict)
- Work in ChangeSets: CS-YYYYMMDD-###
- Small commits allowed (micro-commits).
- Orchestrator pushes branches, opens PRs, fixes CI failures on the same PR, and merges only when allowed.

# Mandatory artifacts (for this run)
- docs/acceptance_contract.md
  - AC-01 must cover the Telegram Q/A round-trip updating status.json
- docs/comms_bootstrap_report.md
  - includes proof steps + failure modes + fallback procedure
- docs/runbook.md
  - how to run the bridge locally
  - how to reset state (status.json cleanup)
  - how to verify end-to-end manually

# Scope guardrails
- Focus ONLY on the Telegram bridge + workflow proof.
- Do not build unrelated product features.
- Avoid overengineering (no DB required unless absolutely necessary).
