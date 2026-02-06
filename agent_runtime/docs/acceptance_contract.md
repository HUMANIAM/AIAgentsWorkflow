---
doc: acceptance_contract
version: 1
owner: system_analyst
last_updated: 2026-02-06
---

# Acceptance Contract: team_communication_bot

## AC-01: Question Polling
**Given** a question in `status.json.client_questions[]` with `delivery_status="pending"`
**When** the bot polls (every 10 seconds)
**Then** the question is detected and processed

**Oracle**: Question `delivery_status` changes from "pending" to "delivered"

## AC-02: GPT Suggestions
**Given** a pending question
**When** the bot processes it
**Then** 3 suggested answers are generated

**Oracle**: Telegram message contains numbered list (1, 2, 3)

## AC-03: Telegram Delivery
**Given** a question with suggestions
**When** sent to client
**Then** client receives formatted message on Telegram

**Oracle**: Client confirms receipt on Telegram

## AC-04: Answer Recording
**Given** client replies on Telegram
**When** bot receives the reply
**Then** answer is written to `status.json.client_answers[]`

**Oracle**: `client_answers[]` contains entry with matching `question_id`

## AC-05: Workflow Continuation
**Given** answer is recorded
**When** `client_action_required` is set to `false`
**Then** orchestrator can continue workflow

**Oracle**: Next `/orchestrator` call advances the workflow
