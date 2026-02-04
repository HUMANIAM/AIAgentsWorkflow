---
role: client
type: owner
mission: Provide intent, answer questions deterministically, approve/reject ACK gates.
---

# Client

## Reply format (for bridge parsing)
`<question_id> = <answer>`

Examples:
- `REQ-ACK-20260203-1 = approve`
- `REQ-ACK-20260203-1 = changes_requested: AC-03 persistence unclear`
- `CS-ACK-CS-20260203-001 = approve`

## Fallback
If Telegram isn't working:
- Edit `status.json.client_answers[]` with source=status_file
- Or answer in chat and ask an agent to copy it into status.json
