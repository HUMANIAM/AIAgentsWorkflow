---
doc: to_development
version: 1
owner: architect_reviewer
last_updated: 2026-02-06
---

# To Development: team_communication_bot

## Approved Architecture
Architecture approved. Implementation already complete in bootstrap_comms phase.

## Implementation Status
- [x] services/openai_client.py - GPT suggestions
- [x] services/status_handler.py - status.json read/write
- [x] apps/telegram/question_poller.py - 10s polling
- [x] apps/telegram/app.py - integrated poller + answer handler
- [x] requirements.txt - openai package added

## Remaining Work
- Update poll interval to 10 seconds ✓ (done)
- Integration test

## AC Checklist
- [ ] AC-01: Question polling (10s)
- [ ] AC-02: GPT suggestions (3 options)
- [ ] AC-03: Telegram delivery
- [ ] AC-04: Answer recording
- [ ] AC-05: Workflow continuation
