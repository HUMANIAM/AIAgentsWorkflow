# Update Bot: New Folder Structure + Idea State Machine

Update the Telegram bot to use `agent_runtime/` as the base path and implement a 4-state idea lifecycle: NEW → PLANNED → ACTIVATED → DONE.

## Idea State Machine

```
/idea stop          /idea plan {id}      /idea activate {id}    /idea done {id}
    ↓                    ↓                      ↓                     ↓
   NEW  ───────────→  PLANNED  ───────────→  ACTIVATED  ───────────→  DONE
```

| State | Trigger | What Happens |
|-------|---------|--------------|
| NEW | `/idea stop` | Brainstorm ends, idea saved to ideas.md |
| PLANNED | `/idea plan {id}` | `context_{idea_id}.md` created in plugin/ |
| ACTIVATED | `/idea activate {id}` | Backup context.md, copy idea context, reset status.json |
| DONE | `/idea done {id}` | Mark idea complete (after team finishes) |

## Commands

| Command | Description |
|---------|-------------|
| `/idea` | Start new brainstorming session |
| `/idea stop` | End session → state=NEW |
| `/idea list {state}` | List ideas by state (new/planned/activated/done, case-insensitive) |
| `/idea plan {id}` | Generate context file → state=PLANNED |
| `/idea activate {id}` | Activate idea for team → state=ACTIVATED |
| `/idea done {id}` | Mark complete → state=DONE |

## Path Changes

| Item | Old Path | New Path |
|------|----------|----------|
| Plugin dir | `repo_root/plugin/` | `repo_root/agent_runtime/plugin/` |
| Status file | `repo_root/status.json` | `repo_root/agent_runtime/status.json` |
| Ideas file | `repo_root/ideas.md` | `repo_root/agent_runtime/ideas.md` |

## Implementation Steps

### 1. Update `idea_handler.py`
- Update paths to use `agent_runtime/`
- Change status values: `IN_PROGRESS` → `NEW`, add `PLANNED`, `ACTIVATED`, `DONE`
- `/idea stop` → saves chat history only, sets NEW (lazy - no GPT call)
- Add `plan_idea(idea_id)` → calls GPT to generate context file, sets PLANNED
- Rename `execute_idea()` to `activate_idea()` → backup context.md, reset status.json, sets ACTIVATED
- Add `complete_idea(idea_id)` → sets DONE
- Add `list_ideas_by_state(state)` function

### 2. Update `idea_chat.py`
- Update command handlers for new state machine
- `/idea stop` → saves idea as NEW (no GPT, no context file)
- `/idea plan {id}` → calls GPT, generates context file, sets PLANNED
- `/idea activate {id}` → activates idea, resets workflow
- `/idea done {id}` → marks complete
- `/idea list {state}` → filter by state (case-insensitive)

### 3. Reset status.json on Activate
When activating an idea, reset to default workflow state:
```json
{
  "problem": { "source": "plugin/context.md", "text": "<headline>" },
  "current_phase": "not_started",
  "phase_status": "pending",
  "actor_status": "pending",
  "gates": { all: "pending" },
  ...
}
```

### 4. Move Files (after bot update)
- Move `ideas.md` → `agent_runtime/ideas.md`
- Move context files → `agent_runtime/plugin/`

## Files to Modify

1. `steward_ai_zorba_bot/services/idea_handler.py`
2. `steward_ai_zorba_bot/apps/telegram/idea_chat.py`
