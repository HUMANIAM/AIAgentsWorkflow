# Commit, Fix Orchestrator, and Verify Full SDLC Flow

Commit current telegram bot work, fix orchestrator to execute silently (no chatbot), then verify the entire flow works with a minimal test task.

---

## Steps

### 1. Commit Current Work
```bash
git add -A
git commit -m "telegram bot implemented"
```

### 2. Fix Orchestrator (Hard Start Algorithm)
Modify `.windsurf/workflows/orchestrator.md`:
- Add Hard Start Algorithm at top
- First output must be tool call, not prose
- Client questions via `client_questions[]` only
- Stop when `client_action_required=true`

### 3. Update Agent Workflows
Ensure all agents follow silent execution:
- No introductions
- Read inputs → do work → write outputs → update status
- Questions go to `client_questions[]`

### 4. Create Test Task
Replace `plugin/context.md` with minimal task:
```
Goal: Build negate(n) function that returns -n
Done when: unit test passes
```

### 5. Reset status.json
- `current_phase`: "bootstrap_comms"
- `current_actor`: "devops"
- `phase_status`: "in_progress"
- Clear old questions/answers
- `client_action_required`: false

### 6. Run and Verify
Execute `/orchestrator` and verify:
- [ ] No chatbot prose
- [ ] `status.json` updated
- [ ] `status_history.csv` appended
- [ ] Phases progress: bootstrap_comms → requirements → architecture → devops → backend → testing → security → done
- [ ] Each agent does its work per charter
- [ ] Client questions delivered via `client_questions[]`

---

## Files to Modify

| File | Change |
|------|--------|
| `.windsurf/workflows/orchestrator.md` | Hard Start Algorithm |
| `.windsurf/workflows/*.md` | Silent execution pattern (if needed) |
| `plugin/context.md` | Test task |
| `status.json` | Reset to initial state |
