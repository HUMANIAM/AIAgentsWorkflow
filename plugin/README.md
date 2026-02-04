# Plugin: steward_ai_zorba_bot (Telegram closed-loop)

This plugin defines the run context for the SDLC agent pipeline.

## What we are building
A minimal Telegram bridge that:
- reads questions from `status.json`
- sends them to the client on Telegram
- ingests replies back into `status.json`
- enables the orchestrator to proceed without manual coordination

## Secrets / configuration
Secrets are stored locally (never committed) in:
- `steward_ai_zorba_bot/.env`

Expected keys:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_ALLOWED_USER_IDS (comma-separated)
- (optional) TELEGRAM_DEFAULT_CHAT_ID

## How the workflow closes the loop
- Agents ask questions via `status.json.client_questions[]`
- Bridge delivers them
- Client replies with: `<question_id> = <answer>`
- Bridge writes answers to `status.json.client_answers[]`
- Orchestrator gates progress based on answered questions + ACKs

## Fallback
If Telegram is not ready:
- set `status.json.comms.state = fallback_only`
- client answers by editing `status.json.client_answers[]`
