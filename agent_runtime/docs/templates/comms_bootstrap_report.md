# Comms Bootstrap Report

## Goal
Prove client Q/A transport works (Telegram preferred, fallback always available).

## Configuration (no secrets)
- Telegram allowed_user_ids:
- How bridge is started (high level):
- Files watched:
- status.json fields used:

## Proof (evidence)
1) Create a client question in status.json
2) Show it arrived to the client (Telegram screenshot or log ref)
3) Client reply processed into status.json.client_answers[]
4) Question marked answered

## Failure modes
- Token missing/invalid
- Wrong user id
- Bridge not running
- Rate limits

## Fallback procedure (always)
If Telegram is not working, client answers by updating status.json.client_answers[] (source=status_file).
