---
plugin: telegram_bridge_pilot
version: 2
owner: client
last_updated: 2026-02-03
---

# Problem (this run)
Build a **Telegram client loop bridge** for the SDLC pipeline:
- Agents write questions into `status.json` (single source of truth).
- A local bridge process sends those questions to the client on Telegram.
- The client replies in Telegram using `<question_id> = <answer>`.
- The bridge writes answers back into `status.json.client_answers[]` and marks questions answered.
- Fallback: if Telegram is not ready, client answers by editing `status.json` directly (or via chat → an agent writes it).

# Stack constraints
- Backend: FastAPI + Python (Linux)
- CI: GitHub Actions (required) — DevOps must implement.
- Repo entrypoints: DevOps must create a single local entrypoint (e.g., `make check`, `make test`) and CI must call it.

# Client comms policy
- Primary channel: Telegram
- Fallback channel: status.json manual replies (status_file)
- Bootstrap phase MUST run first:
  - either prove Telegram works OR explicitly set comms.state=fallback_only.

# Secrets (provided by client; never committed)
- TELEGRAM_BOT_TOKEN
- TELEGRAM_ALLOWED_USER_IDS (client Telegram user id)
- (optional) TELEGRAM_DEFAULT_CHAT_ID
- (optional) GITHUB_TOKEN if using GitHub MCP server

# ChangeSet policy
- commit_cap: 50 micro-commits per ChangeSet
- only orchestrator merges to main: true
- client ack required for merge: true (ChangeSet ACK via Telegram/fallback)

# Required client ACK gates
- Requirements ACK is mandatory before architecture starts.
- Final ACK is mandatory before done.

# Evidence rule
No one is allowed to claim "done" without evidence:
- measurable AC oracles
- test reports
- CI green on branch before merge (DevOps defines exact workflow)
