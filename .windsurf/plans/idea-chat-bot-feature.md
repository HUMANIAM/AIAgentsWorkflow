# Idea Chat Bot Feature

Extend the Telegram bot with `/idea` commands for brainstorming ideas with GPT, saving conversations, and converting them to team contexts.

---

## Commands

| Command | Action |
|---------|--------|
| `/idea` | Start new idea session - bot asks "What do you have in mind?" |
| `/idea stop` | End current session - GPT generates `context_{idea}.md` from chat |
| `/idea list` | Show all ideas with headlines |
| `/idea execute <id>` | Copy `context_{idea}.md` → `context.md` and update `status.json` |

---

## Flow 1: New Idea Session

**Key: GPT receives FULL chat history on every message (not just current message)**

```
User: /idea
Bot: 💡 What do you have in mind? Tell me your idea.

User: I want a dashboard to track team progress
Bot: [Records message #1 to ideas.md]
     [Sends to GPT: history=[msg1]]
     📝 GPT says: "Great idea! A dashboard could show..."
     [Records GPT response to ideas.md]

User: What about blocked tasks?
Bot: [Records message #2 to ideas.md]
     [Sends to GPT: history=[msg1, gpt1, msg2]]  ← FULL HISTORY
     📝 GPT says: "For blocked tasks, consider..."
     [Records GPT response to ideas.md]

User: Can it show who is blocking?
Bot: [Records message #3 to ideas.md]
     [Sends to GPT: history=[msg1, gpt1, msg2, gpt2, msg3]]  ← FULL HISTORY
     📝 GPT says: "Yes, you could add assignee info..."

User: /idea stop
Bot: [Sends FULL history to GPT with prompt: "Generate context document"]
     [GPT creates structured context from entire conversation]
     ✅ Idea session ended.
     📄 Created: plugin/context_dashboard_tracker.md
     💡 Headline: "Dashboard for Team Progress Tracking"
```

**Memory mechanism:**
- Every message appends to `ideas.md` under the current idea
- On each user message, bot loads FULL history from `ideas.md` and sends to GPT
- GPT always has complete conversation context
- On `/idea stop`, GPT receives full history + prompt to generate context.md

---

## Flow 2: List Ideas

```
User: /idea list
Bot: 📋 Your Ideas:
    1. [ID: dashboard_tracker] Dashboard for Team Progress Tracking
    2. [ID: theme_customization] App Theme Customization
    3. [ID: notification_system] Smart Notification System
```

---

## Flow 3: Execute Idea

```
User: /idea execute dashboard_tracker
Bot: ✅ Activated idea: "Dashboard for Team Progress Tracking"
    - Copied to plugin/context.md
    - Updated status.json problem text
    
    Run /orchestrator to start the team on this!
```

---

## File Structure

### `ideas.md`
```markdown
# Ideas Log

---
## ID: dashboard_tracker
**Headline:** Dashboard for Team Progress Tracking
**Created:** 2026-02-06 01:30
**Status:** NEW

### Chat History
**User:** I want a dashboard to track team progress
**GPT:** Great idea! A dashboard could show task completion rates...
**User:** What about blocked tasks?
**GPT:** For blocked tasks, consider visual indicators...

---
## ID: theme_customization
**Headline:** App Theme Customization
**Created:** 2026-02-05
**Status:** EXECUTED
**Context File:** plugin/context_theme_customization.md

### Chat History
...
```

### `plugin/context_{idea_id}.md` (generated on `/idea stop`)
```markdown
---
plugin: dashboard_tracker
version: 1
owner: client
last_updated: 2026-02-06
---

# What I want (client perspective)
[GPT-generated summary from chat]

## The problem I have now:
[Extracted from conversation]

## What I need:
[Extracted from conversation]

## What "done" means to me:
[Extracted from conversation]
```

---

## Implementation

### 1. `services/idea_handler.py` (new)
```python
- create_idea(user_id) → idea_id  # Start new idea, return ID
- add_message(idea_id, role, text)  # Append to chat history
- get_chat_history(idea_id) → list  # Get full history for GPT
- list_ideas() → list  # Return all ideas with headlines
- generate_context(idea_id) → path  # Create context_{id}.md
- execute_idea(idea_id)  # Copy to context.md, update status.json
- get_active_idea(user_id) → idea_id  # Get current session
- end_idea(idea_id)  # Mark session ended
```

### 2. `services/openai_client.py` (update)
```python
- chat_about_idea(history: list, new_message: str) → str
  # Send full history + new message, get GPT response
  
- generate_idea_headline(history: list) → (headline, description)
  # Ask GPT to summarize idea into headline + brief description
  
- generate_context_from_chat(history: list) → str
  # Ask GPT to create context.md content from chat
```

### 3. `apps/telegram/app.py` (update)
```python
handle_message():
    if text.startswith('/idea'):
        → parse command (stop, list, execute, or new)
        → route to idea_handler
    elif has_active_idea_session(user_id):
        → continue idea chat (poll, record, GPT, respond)
    elif has_pending_team_question:
        → current behavior
    else:
        → acknowledge
```

### 4. `apps/telegram/idea_chat.py` (new)
```python
class IdeaSession:
    - start() → ask "What do you have in mind?"
    - process_message(text) → record, GPT, respond
    - stop() → generate context, end session
    - list_all() → format idea list
    - execute(idea_id) → activate idea
```

---

## GPT Prompts

### For idea chat:
```
You are helping a client brainstorm a software idea.
Be concise, ask clarifying questions, suggest features.
Keep responses under 100 words.

Chat history:
{history}

User: {new_message}
```

### For headline generation:
```
Based on this conversation, generate:
1. A short headline (5-7 words)
2. A brief description (1 sentence)

Respond as JSON: {"headline": "...", "description": "..."}
```

### For context generation:
```
Convert this brainstorming chat into a client context document.
Extract: what they want, their current problem, requirements, done criteria.

Chat:
{history}

Output in markdown format matching plugin/context.md structure.
```

---

## Key Design Decisions

1. **Full history to GPT**: Every message sends complete chat history so GPT has context
2. **Persistent storage**: `ideas.md` survives bot restarts
3. **ID-based**: Each idea gets a slug ID (e.g., `dashboard_tracker`)
4. **Separate contexts**: Each idea gets `context_{id}.md`, only copied to main on execute
5. **Status tracking**: NEW → EXECUTED when `/idea execute` is called

---

## Ready?

Say **"go"** to implement this feature.
