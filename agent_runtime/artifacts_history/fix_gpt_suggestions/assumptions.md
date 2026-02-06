---
doc: assumptions
version: 1
owner: system_analyst
last_updated: 2026-02-06
---

# Assumptions: team_communication_bot

## A-01: Environment
- Python 3.8+ available
- OpenAI API accessible
- Telegram Bot API accessible

## A-02: Configuration
- `AI_API_KEY` in `.env` is valid
- `TELEGRAM_BOT_TOKEN` in `.env` is valid
- `TELEGRAM_ALLOWED_USER_IDS` contains client user ID

## A-03: Existing Infrastructure
- `steward_ai_zorba_bot` structure exists
- Bot can be started with `python main.py`

## A-04: Client Availability
- Client has Telegram app installed
- Client can respond within reasonable time
