---
doc: runbook
version: 2
owner: devops
purpose: "How to run, reset, verify, debug. Must match CI entrypoints."
last_updated: 2026-02-03
---

# Runbook

## Golden rule
CI and local must use the **same entrypoints** (e.g., `make check`, `make test`).

## System Overview
- Components: steward_ai_zorba_bot (Telegram bridge)
- Ports/URLs: Local Telegram bot polling
- Env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS, TELEGRAM_DEFAULT_CHAT_ID

## Run Locally
- Setup: `make dev-setup`
- Run backend: `python -m steward_ai_zorba_bot.main`
- Run frontend (if any): N/A
- Stop: Ctrl+C or kill process

## Reset / Clean State
- Deterministic reset steps:
  1. `make clean` - Clean temporary files
  2. Reset status.json: Edit `status.json` to clear questions/answers
  3. Restart bridge: `python -m steward_ai_zorba_bot.main`
  - Optional helper: `python orchestrator.py restart --apply --clear-qa --clear-acks`

## Verify
- Smoke check: `make validate` - Validates JSON and required files
- Tests: `make test` - Run pytest tests
- Lint/format-check: `make check` - Runs all CI checks locally
- Individual checks: `make lint`, `make format`, `make typecheck`, `make security`

## Workflow orchestration (debug)
If `/orchestrator` gets stuck or the workflow state looks inconsistent:
- Validate: `python orchestrator.py validate`
- Reconcile obvious gate inconsistencies: `python orchestrator.py reconcile --apply`
- Advance one orchestrator transition (delegating): `python orchestrator.py step --apply`

## Debug
- Logs: Check bridge output and Telegram bot logs
- Common failures:
  - Missing Telegram token: Set in steward_ai_zorba_bot/.env
  - Invalid user ID: Verify allowed_user_ids in status.json
  - JSON format errors: Run `make validate`

## Security Notes
- Secrets: Never commit TELEGRAM_BOT_TOKEN, use .env file
- Defaults: Fallback to status_file mode if Telegram unavailable

## CI Entrypoints
- Full CI check: `make check` (runs lint, format, typecheck, security, validate)
- Tests only: `make test`
- Install deps: `make install`
- Auto-fix: `make fix` (formatting and lint fixes)
