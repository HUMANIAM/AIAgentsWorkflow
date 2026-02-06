# Steward AI Zorba Bot 🤖

**The Client Communication Bridge for the AI Software Development Team**

This bot is the **sole communication channel** between the AI development team and the human client. It bridges the gap between autonomous AI agents working on software projects and the client who needs to provide input, answer questions, and approve decisions.

---

## Role in the Team

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI SOFTWARE DEVELOPMENT TEAM                  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ DevOps   │  │ Analyst  │  │ Architect│  │ Backend  │  ...   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                           │                                      │
│                    ┌──────┴──────┐                              │
│                    │ status.json │  ← Single source of truth    │
│                    └──────┬──────┘                              │
│                           │                                      │
│              ┌────────────┴────────────┐                        │
│              │  STEWARD AI ZORBA BOT   │  ← YOU ARE HERE        │
│              │  (This Bot)             │                        │
│              └────────────┬────────────┘                        │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │    TELEGRAM   │
                    │    (Client)   │
                    └───────────────┘
```

## What This Bot Does

### 1. **Delivers Team Questions to Client** 📋
When AI agents need client input, they write questions to `status.json`. This bot:
- Polls `status.json` every 10 seconds for pending questions
- Generates **AI-powered suggested answers** using GPT-4o
- Delivers questions to the client via Telegram with suggestions
- Records client answers back to `status.json`

### 2. **Enables Client-AI Conversation** 💬
- Client receives questions with 3 smart suggestions
- Client can reply with a number (1, 2, 3) or type custom answer
- Bot records answer and notifies the team to continue

### 3. **Idea Brainstorming Mode** 💡
Brainstorm ideas with GPT and manage them through a 4-state lifecycle:

```
NEW → PLANNED → ACTIVATED → DONE
```

| Command | Description | State Change |
|---------|-------------|--------------|
| `/idea` | Start brainstorming session with GPT | - |
| `/idea stop` | Save idea with headline | → NEW |
| `/idea list {state}` | List ideas by state (new/planned/activated/done) | - |
| `/idea plan <id>` | Generate context file from chat | → PLANNED |
| `/idea activate <id>` | Activate for team (backup context.md, reset status.json) | → ACTIVATED |
| `/idea done <id>` | Mark idea complete | → DONE |

**Workflow:**
1. `/idea` - Chat with GPT about your idea
2. `/idea stop` - Save when done brainstorming
3. `/idea plan <id>` - Generate context file (calls GPT)
4. `/idea activate <id>` - Activate for team to work on
5. `/idea done <id>` - Mark complete after team finishes

---

## How It Works

### Question Flow
```
1. AI Agent writes question to status.json
   └─ client_questions[]: { id, question, context, delivery_status: "pending" }

2. Bot polls status.json (every 10 seconds)
   └─ Finds pending question

3. Bot calls GPT-4o for smart suggestions
   └─ "What color should the app be?" → ["Blue (professional)", "Dark mode", "Let team decide"]

4. Bot sends to Telegram
   └─ 📋 Question from DevOps: ...
      💡 Suggested answers: 1. Blue... 2. Dark... 3. Let team...

5. Client replies (number or custom text)
   └─ "2" or "I prefer green"

6. Bot writes answer to status.json
   └─ client_answers[]: { question_id, answer, source: "telegram" }
   └─ Sets client_action_required: false

7. AI team continues working
```

---

## Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key (for GPT suggestions)

### Installation

```bash
cd steward_ai_zorba_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USER_IDS=your_telegram_user_id
AI_API_KEY=your_openai_api_key
```

### Run

```bash
python main.py
```

The bot will:
- Start polling Telegram for messages
- Poll `status.json` for pending questions
- Deliver questions with GPT suggestions
- Record answers back to `status.json`

---

## Architecture

```
steward_ai_zorba_bot/
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── .env                       # Configuration (not in git)
│
├── apps/
│   └── telegram/
│       ├── app.py             # Main bot class, message handling
│       ├── question_poller.py # Polls status.json, delivers questions
│       ├── bot_config.py      # Configuration & validation
│       ├── telegram_handler.py# Telegram API wrapper
│       └── console_logger.py  # Emoji-prefixed logging
│
├── services/
│   ├── status_handler.py      # Read/write status.json
│   └── openai_client.py       # GPT-4o integration for suggestions
│
└── tests/
    └── test_services.py       # Unit tests
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `question_poller.py` | Polls `status.json` every 10s for pending questions |
| `openai_client.py` | Generates smart answer suggestions via GPT-4o |
| `status_handler.py` | Reads/writes questions and answers to `status.json` |
| `app.py` | Handles incoming Telegram messages, routes to handlers |

---

## Integration with AI Team

### status.json Interface

The bot reads and writes to `../agent_runtime/status.json`:

**Reading (questions from team):**
```json
{
  "client_questions": [
    {
      "id": "Q-DEVOPS-001",
      "from_agent": "DevOps",
      "question": "What color should the app theme be?",
      "context": "Designing the UI",
      "delivery_status": "pending"
    }
  ]
}
```

**Writing (answers from client):**
```json
{
  "client_answers": [
    {
      "question_id": "Q-DEVOPS-001",
      "answer": "Blue and white, professional look",
      "source": "telegram",
      "answered_at": "2026-02-06T01:30:00Z"
    }
  ],
  "client_action_required": false
}
```

---

## Dependencies

```
python-telegram-bot==21.3
python-dotenv==1.0.1
openai==1.6.1
httpx==0.27.0
```

---

## Troubleshooting

### Bot doesn't receive messages
- Check `.env` has correct `TELEGRAM_BOT_TOKEN`
- Verify your user ID is in `TELEGRAM_ALLOWED_USER_IDS`
- Ensure only one bot instance is running

### GPT suggestions show generic fallback
- Check `AI_API_KEY` in `.env` is valid
- Verify OpenAI account has credits
- Check `httpx==0.27.0` is installed (version compatibility)

### Questions not delivered
- Verify `status.json` exists in parent directory
- Check questions have `delivery_status: "pending"`
- Look for errors in console logs

---

## Related Files

| File | Purpose |
|------|---------|
| `../agent_runtime/status.json` | Single source of truth for workflow state |
| `../agent_runtime/plugin/context.md` | Current task context for the team |
| `../agent_runtime/ideas.md` | Ideas log with chat history |
| `../agent_runtime/docs/workflow_protocol.md` | SDLC workflow rules |

---

**Bot Status:** ✅ Production Ready | **Last Updated:** 2026-02-06
