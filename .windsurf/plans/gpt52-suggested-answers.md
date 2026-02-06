# Close the Loop: Bot + GPT-5.2 + Client Communication Test

Implement the full client communication loop where agents write questions to `status.json`, bot polls and delivers them with GPT-5.2 suggestions via Telegram, client answers, bot updates status, and orchestrator continues.

---

## The Loop (What We're Testing)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Agent writes question    Bot polls status.json                 │
│  to status.json      ───► finds pending question                │
│  sets client_action_      calls GPT-5.2 for suggestions         │
│  required=true            sends to Telegram                     │
│                                  │                              │
│                                  ▼                              │
│                           CLIENT (You on Telegram)              │
│                           receives question + suggestions       │
│                           replies with answer                   │
│                                  │                              │
│                                  ▼                              │
│  Orchestrator wakes up    Bot receives answer                   │
│  invokes waiting agent ◄── writes to status.json               │
│  workflow continues        sets client_action_required=false    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Success = You receive a Telegram message, reply, and workflow continues automatically.**

---

## Key Clarifications (From You)

1. **Bot is the ONLY communicator** - Agents never talk to client directly
2. **Bot owns `client_action_required`** - Sets to `false` when answer received
3. **Orchestrator wakes up** - Detects `client_action_required=false`, invokes waiting agent
4. **API key exists** - `AI_API_KEY` already in `steward_ai_zorba_bot/.env`

---

## Implementation Plan

### Phase 1: OpenAI Client Module
- [ ] Create `steward_ai_zorba_bot/services/openai_client.py`
- [ ] Use existing `AI_API_KEY` from `.env`
- [ ] Function: `get_suggestions(question, context) → List[str]`

### Phase 2: Status.json Handler
- [ ] Create `steward_ai_zorba_bot/services/status_handler.py`
- [ ] Read/write `status.json` (path: `../../status.json` from bot)
- [ ] Functions: `get_pending_questions()`, `write_answer()`, `set_client_action_required()`

### Phase 3: Question Delivery Loop
- [ ] Create `steward_ai_zorba_bot/apps/telegram/question_poller.py`
- [ ] Poll `status.json.client_questions[]` for `delivery_status="pending"`
- [ ] Call GPT-5.2 for suggestions
- [ ] Send formatted message to client via Telegram
- [ ] Update `delivery_status="delivered"`

### Phase 4: Answer Handler
- [ ] Modify `steward_ai_zorba_bot/apps/telegram/app.py`
- [ ] When client replies, match to pending question
- [ ] Write answer to `status.json.client_answers[]`
- [ ] Set `client_action_required=false`

### Phase 5: Test Task
- [ ] Update `plugin/context.md` with new task requiring client input
- [ ] Reset `status.json` to `bootstrap_comms`
- [ ] Run bot in background
- [ ] Run `/orchestrator`
- [ ] Verify: question arrives on Telegram with suggestions
- [ ] Reply and verify: workflow continues

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `steward_ai_zorba_bot/services/__init__.py` | Create | Package init |
| `steward_ai_zorba_bot/services/openai_client.py` | Create | GPT-5.2 API calls |
| `steward_ai_zorba_bot/services/status_handler.py` | Create | Read/write status.json |
| `steward_ai_zorba_bot/apps/telegram/question_poller.py` | Create | Poll & deliver questions |
| `steward_ai_zorba_bot/apps/telegram/app.py` | Modify | Integrate poller + answer handler |
| `plugin/context.md` | Modify | Test task requiring client input |

---

## Message Format (Telegram)

```
📋 Question from [agent]:

[question text]

💡 Suggested answers:
1. [suggestion 1]
2. [suggestion 2]
3. [suggestion 3]

Reply with 1, 2, 3, or type your own answer.
```

---

## Test Scenario

**Task**: "Build a greeting app that says hello in the user's preferred language"

**Expected Flow**:
1. System Analyst asks: "What languages should be supported?"
2. Bot sends to Telegram with GPT suggestions: "1. English only, 2. English + Spanish, 3. Multiple languages"
3. You reply: "2"
4. Bot writes answer, sets `client_action_required=false`
5. Orchestrator continues, System Analyst uses your answer

---

## Ready?

**CONFIRMED** - User has updated `plugin/context.md` with the new task.

### Next Steps (in order):
1. Reset `status.json` to `bootstrap_comms` phase
2. Implement the bot features (OpenAI client, status handler, question poller)
3. Run bot in background
4. Run `/orchestrator` to test the loop

Say **"go"** to start implementation.
