# Acceptance Contract (AC)

## Rules
- Each AC must be measurable.
- Each AC must have an oracle (how pass/fail is observed).

## AC Template
### AC-01: <title>
**Given** ...
**When** ...
**Then** ...

**Oracle**:
- Transport/UI:
- API:
- Persistence (refresh/restart):
- Logs/Evidence:

**Pass/Fail**:
- Pass if ...
- Fail if ...

---

## Minimum required AC for this project
- One AC proving Telegram bridge Q/A round-trip updates status.json
