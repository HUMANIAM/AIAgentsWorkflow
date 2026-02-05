# Test Orchestrator Flow with Minimal Task

Fix orchestrator.md, then verify the entire SDLC flow works using a trivial "negate a number" task before applying to real projects.

---

## Approach

1. **Backup** current `plugin/context.md` and `status.json`
2. **Create minimal test task**: "Build a Python function that negates a number"
3. **Reset** `status.json` to `bootstrap_comms` phase
4. **Fix** `orchestrator.md` with Hard Start Algorithm
5. **Run** `/orchestrator` and verify:
   - No chatbot behavior (no introductions/prose)
   - First output is file read/write
   - Flow progresses through phases
   - `status_history.csv` gets appended
6. **Restore** original files after test

---

## Test Task Definition

```markdown
# Goal (this run)
Build `negate_number`: a Python function that returns the negation of an input number.

Definition of done:
1) Function `negate(n)` returns `-n`
2) Unit test passes
3) Code in `src/negate.py`
```

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `plugin/context.md` | Backup → replace with test task |
| `status.json` | Reset to `bootstrap_comms`, clear questions/answers |
| `.windsurf/workflows/orchestrator.md` | Add Hard Start Algorithm |
| `status_history.csv` | Will be appended during test |

---

## Verification Checklist

- [ ] `/orchestrator` first action is `read_file` (not prose)
- [ ] `status.json` updated with phase transition
- [ ] `status_history.csv` row appended
- [ ] Next agent invoked (e.g., `/devops`)
- [ ] No "Hello, I am the orchestrator..." type output
- [ ] When `client_action_required=true`, orchestrator stops

---

## Rollback

After test:
- Restore `plugin/context.md.bak` → `plugin/context.md`
- Optionally keep test `status.json` or restore backup
