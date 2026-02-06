---
role: client
type: owner
mission: Provide intent, answer questions deterministically, approve/reject ACK gates.
---

# Client

## Reply format (for bridge parsing)
`<question_id> = <answer>`

Examples:
- `REQ-CONFIRM-<timestamp> = confirm` (confirm understanding)
- `REQ-CONFIRM-<timestamp> = clarify: <clarification>` (request clarification)
- `REQ-ACK-20260203-1 = approve`
- `REQ-ACK-20260203-1 = changes_requested: AC-03 persistence unclear`
- `CS-ACK-CS-20260203-001 = approve`

## Requirements Confirmation (MANDATORY)
Before the system analyst proceeds with full requirements work, you MUST confirm their understanding:
- Review the summary presented by the system analyst
- Reply with `REQ-CONFIRM-<id> = confirm` to proceed
- Reply with `REQ-CONFIRM-<id> = clarify: <your clarification>` if something is unclear

## Fallback
If Telegram isn't working:
- Edit `agent_runtime/status.json.client_answers[]` with source=status_file
- Or answer in chat and ask an agent to copy it into status.json
