# Fix Orchestrator: Hard Start Algorithm (No Chatbot Behavior)

Rewrite `orchestrator.md` to enforce silent execution - first output must be `status.json` update, not prose.

---

## Problem

When `/orchestrator` is invoked, it acts like a chatbot:
- Introduces itself
- Describes what it will do
- Talks instead of executing

**Expected behavior:** Silent execution → update `status.json` → append `status_history.csv` → invoke next agent

---

## Root Cause

`orchestrator.md` lacks:
1. A **Hard Start Algorithm** at the top forcing immediate action
2. A rule: "First output must be a file write, not prose"
3. Clear instruction: "If you need to ask the client, write to `client_questions[]` and set `client_action_required=true`"

---

## Plan

### 1. Rewrite `orchestrator.md` with Hard Start Section

Add at the **very top** (after frontmatter):

```markdown
## ⚠️ HARD START ALGORITHM (MANDATORY)

On `/orchestrator` invocation:
1. **DO NOT** speak, greet, describe, or explain
2. **DO NOT** output prose before file operations
3. **IMMEDIATELY** execute steps A→E below

### Step A: Read State
- Read `status.json`
- Read `plugin/context.md` (problem definition)

### Step B: Determine Action
- If `current_phase=done` → output "Workflow complete" and stop
- If `client_action_required=true` → stop (waiting for client via Telegram)
- Else → compute next transition

### Step C: Update status.json
- Apply transition (phase/actor/status changes)
- Write `status.json` atomically

### Step D: Append status_history.csv
- One row per transition

### Step E: Invoke Next Agent
- Call the workflow for `current_actor` (e.g., `/system_analyst`)
- Do NOT do their work - just invoke them

### Client Communication Rule
- **NEVER** speak to client directly in chat
- Write questions to `status.json.client_questions[]`
- Set `client_action_required=true`
- Telegram bot will deliver and collect answers
```

### 2. Add Explicit "No Prose" Rules

```markdown
## Output Rules (Non-Negotiable)

1. First output of any `/orchestrator` run MUST be a tool call (read/write file)
2. No greetings, no introductions, no "I will now..."
3. Status updates go to `status.json`, not chat
4. If blocked waiting for client: set `client_action_required=true` and STOP
```

### 3. Simplify the Flow Section

Remove verbose explanations. Keep only the state machine:

```
Phase Flow:
  owner(not_started) → owner(in_progress) → owner(completed) 
  → reviewer(in_review) → reviewer(approved|changes_requested)
  → next_phase OR retry_owner
```

---

## Files to Modify

| File | Change |
|------|--------|
| `.windsurf/workflows/orchestrator.md` | Add Hard Start Algorithm at top, add No Prose rules |

---

## Success Criteria

- [ ] `/orchestrator` first output is a tool call (read_file or edit)
- [ ] No chatbot-like introductions
- [ ] `status.json` updated before any prose
- [ ] `status_history.csv` appended on transitions
- [ ] Client questions go to `client_questions[]`, not chat
- [ ] When `client_action_required=true`, orchestrator stops and waits
