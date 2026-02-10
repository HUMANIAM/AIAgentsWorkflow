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
Brainstorm ideas with GPT and run them through activation/execution:

```
NEW → REFINING → REFINED → PLANNED → ACTIVATED → EXECUTING → WAITING_REALIZATION_APPROVAL → DONE
```

| Command | Action |
|---------|--------|
| `/idea` | Start prompt mode - bot asks "What do you have in mind?" |
| `/idea <headline>` | Start new refining session with GPT-refined headline and idea ID |
| `/idea start <id>` | Resume an existing idea session (`/idea continue <id>` alias) |
| `/idea stop` | Close active session and mark idea `REFINED` |
| `/idea list` | Show your idea files and statuses |
| `/idea plan <id>` | Generate `context_<id>.md` from idea history and mark `PLANNED` |
| `/idea activate <id>` | Overwrite `context.md` from `context_<id>.md` and mark idea `ACTIVATED` (`/idea active <id>` alias) |
| `/idea execute <id>` | Trigger orchestrator `init` + autonomous `run` for the `ACTIVATED` idea |
| `/idea done <id>` | Mark idea `DONE` (allowed only from `WAITING_REALIZATION_APPROVAL`) |

**Workflow:**
1. `/idea <headline>` - GPT refines title and starts session
2. Chat with GPT to refine requirements
3. `/idea stop` - freeze brainstorm as `REFINED`
4. `/idea plan <id>` - generate PM/BA context
5. `/idea activate <id>` - overwrite `context.md`, set status `ACTIVATED`
6. `/idea execute <id>` - run orchestrator autonomously (requires `ACTIVATED` + matching `context.md` `idea_id`)
7. Orchestrator pauses at required human gates and bot asks for approval on Telegram
8. Approval resumes run automatically; on completed realization the idea is marked `DONE`

Current Version2 execution mode is simulation-first: roles are impersonated by orchestrator to generate SDLC artifacts/evidence, not full product code implementation.
Run artifacts are isolated per idea under `Version2/agent_runtime/artifacts/<idea_headline_slug>/`.

For realization runs, `/orchestrator` is an agent-input trigger (`python Version2/tools/src/orchestrator/main.py trigger '/orchestrator'`), not a Telegram command.
Telegram remains the human communication and approval channel.

---

## How It Works

### Question Flow
```
1. Orchestrator/AI roles write question to status.json
   └─ questions[]: { id, from_role, status: "pending_delivery" }

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
   └─ answers[] appended with mapped question_id

7. AI team continues working
```

### Governance Gate Replies
- For gate questions (`Q-GATE-*`), reply with strict tokens:
  - Approve: `approve`, `approved`, `yes`, `1`
  - Reject: `reject`, `rejected`, `no`, `2`
- Any other reply asks for clarification and keeps gate waiting.

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
AGENT_RUNTIME_DIR=Version2/agent_runtime
AI_API_KEY=your_openai_api_key
ORCHESTRATOR_PROFILE=default_fallback_profile
ORCHESTRATOR_MIDFLOW_HUMAN_GATES=NONE
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
  "questions": [
    {
      "id": "Q-DEVOPS-001",
      "from_role": "devops_engineer",
      "to_human": true,
      "required": true,
      "question": "What color should the app theme be?",
      "context": "Designing the UI",
      "status": "pending_delivery",
      "created_at": "2026-02-06T01:29:00Z"
    }
  ]
}
```

**Writing (answers from client):**
```json
{
  "answers": [
    {
      "question_id": "Q-DEVOPS-001",
      "answer": "Blue and white, professional look",
      "source": "telegram",
      "answered_at": "2026-02-06T01:30:00Z"
    }
  ]
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
- Verify `status.json` exists in runtime directory
- Check `questions[]` entries have `status: "pending_delivery"`
- Look for errors in console logs

---

## Related Files

| File | Purpose |
|------|---------|
| `<AGENT_RUNTIME_DIR>/status.json` | Single source of truth for workflow state |
| `<AGENT_RUNTIME_DIR>/plugin/context.md` | Current active context for the team |
| `<AGENT_RUNTIME_DIR>/plugin/context_template.md` | Mandatory template contract for GPT context generation |
| `<AGENT_RUNTIME_DIR>/plugin/context_<idea>.md` | Idea-specific generated context files |
| `<AGENT_RUNTIME_DIR>/ideas/<idea>.md` | Canonical per-idea files with metadata + chat history |

---

**Bot Status:** ✅ Production Ready | **Last Updated:** 2026-02-06
