# Enable All Agents to Ask Questions via Telegram Bridge

Complete the Telegram bridge integration so any agent can ask the client questions through `status.json`, and the bot delivers/receives answers via Telegram.

---

## Current State

| Component | Status |
|-----------|--------|
| `status.json` schema | ✅ Has `client_questions[]` and `client_answers[]` |
| Agent workflows | ⚠️ Only `system_analyst.md` explicitly mentions writing questions |
| Telegram bot | ❌ Only echoes messages - no `status.json` bridge |
| Orchestrator | ✅ Manages phase transitions |

---

## Plan

### Phase 1: Implement Telegram ↔ status.json Bridge
**Goal:** Bot watches `status.json`, sends pending questions, parses replies, writes answers back.

1. **Create `status_bridge.py`** in `steward_ai_zorba_bot/apps/telegram/`
   - Watch `status.json` for questions with `delivery_status=pending`
   - Send question to Telegram (format: `[ID] Question\nOptions: ...\nReply: <ID> = <answer>`)
   - Update `delivery_status=sent`, `delivered_at`
   - Parse incoming replies matching `<ID> = <answer>` pattern
   - Write to `client_answers[]`, mark question `is_answered=true`

2. **Integrate bridge into `app.py`**
   - Run bridge watcher as background task alongside message handler
   - Handle both outgoing (questions) and incoming (answers) flows

### Phase 2: Update Agent Workflows to Allow Questions
**Goal:** All agents can write questions to `status.json.client_questions[]`.

3. **Add question-asking protocol to `docs/workflow_protocol.md`**
   - Define standard question format
   - Specify required fields: `id`, `question`, `options`, `recommendation`, `required_reply_format`

4. **Update agent workflows** (add question capability):
   - `backend.md`
   - `backend_tester.md`
   - `frontend.md`
   - `frontend_tester.md`
   - `integration_tester.md`
   - `security.md`
   - `devops.md`
   - `architect.md`

### Phase 3: Verification
5. **Add integration test** for the bridge
6. **Manual test** - start bot, add question to `status.json`, verify Telegram delivery and reply handling

---

## Question Format (Standard)

```json
{
  "id": "<ROLE>-<PHASE>-<NNN>",
  "question": "Clear question text",
  "delivery_status": "pending",
  "is_answered": false,
  "created_at": "ISO timestamp",
  "options": ["opt1", "opt2"],
  "recommendation": "opt1",
  "required_reply_format": "<ID> = <answer>"
}
```

**ID Convention:** `<ROLE>-<NNN>` (e.g., `BE-001`, `SEC-001`, `FE-001`)

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `steward_ai_zorba_bot/apps/telegram/status_bridge.py` | **Create** - bridge logic |
| `steward_ai_zorba_bot/apps/telegram/app.py` | **Modify** - integrate bridge |
| `docs/workflow_protocol.md` | **Modify** - add question protocol |
| `.windsurf/workflows/*.md` (8 files) | **Modify** - add question capability |
| `steward_ai_zorba_bot/tests/telegram/test_status_bridge.py` | **Create** - tests |

---

## Success Criteria

- [ ] Any agent can write a question to `status.json.client_questions[]`
- [ ] Bot sends pending questions to Telegram within polling interval
- [ ] Client replies with `<ID> = <answer>` format
- [ ] Bot writes answer to `status.json.client_answers[]`
- [ ] Question marked `is_answered=true`
- [ ] All existing tests pass
- [ ] New bridge tests pass
