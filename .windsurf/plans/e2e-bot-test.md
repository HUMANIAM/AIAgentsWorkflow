# End-to-End Bot Communication Test

Test the full loop: I run bot → write question to status.json → you receive on Telegram with 3 GPT suggestions → you answer → bot writes to status.json → I confirm.

---

## Test Steps

### Step 1: I start the bot
```bash
cd steward_ai_zorba_bot
source .venv/bin/activate
python main.py
```

### Step 2: I write a test question to status.json
Add to `client_questions[]`:
```json
{
  "id": "Q-TEST-E2E",
  "from_agent": "Orchestrator",
  "question": "What is your favorite color for the app theme?",
  "context": "Testing the communication loop",
  "delivery_status": "pending",
  "created_at": "2026-02-06T00:45:00Z"
}
```
Set `client_action_required: true`

### Step 3: You receive on Telegram
Within 10 seconds, you should receive:
```
📋 Question from Orchestrator:

What is your favorite color for the app theme?

💡 Suggested answers:
1. [GPT suggestion 1]
2. [GPT suggestion 2]
3. [GPT suggestion 3]

Reply with 1, 2, 3, or type your own answer.
```

### Step 4: You reply
Reply with "1", "2", "3", or your own text.

### Step 5: Bot updates status.json
- Writes your answer to `client_answers[]`
- Sets `client_action_required: false`

### Step 6: I confirm
I read `status.json` and confirm your answer is recorded.

---

## Ready?

Say **"go"** and I'll start the bot and write the test question.
