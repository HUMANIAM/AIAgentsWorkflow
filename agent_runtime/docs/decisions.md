---
doc: decisions
version: 1
owner: system_analyst
last_updated: 2026-02-06
---

# Decisions: team_communication_bot

## D-01: Poll Interval
**Decision**: 10 seconds
**Rationale**: Client explicitly requested "Within 10 seconds" response time
**Source**: Q-REQ-001 answer

## D-02: GPT Model
**Decision**: Use gpt-4o (GPT-5.2 equivalent)
**Rationale**: Best available model for generating helpful suggestions
**Fallback**: Generic suggestions if API fails

## D-03: Suggestion Count
**Decision**: 3 suggestions per question
**Rationale**: Enough options without overwhelming client
