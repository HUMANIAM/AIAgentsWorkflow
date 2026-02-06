# Multi-Agent Stress Test Plan

Run the fix_gpt_suggestions task through the full SDLC workflow to identify potential issues when different agents (not a single model) execute the charters.

---

## Objective

Execute the workflow with the new `fix_gpt_suggestions` context and document any issues that could break the system when:
- Different agents handle different phases
- Handoffs between agents occur
- Client communication happens via Telegram
- Status.json is read/written by multiple actors

---

## Potential Breaking Points to Watch

| Area | Risk | What to Watch |
|------|------|---------------|
| **status.json consistency** | Race conditions | Two agents writing simultaneously |
| **Phase transitions** | Lost state | Actor doesn't update status before handoff |
| **Client questions** | Stuck workflow | `client_action_required` not cleared |
| **Artifact references** | Missing files | Agent references doc that doesn't exist |
| **Review loops** | Infinite loop | Reviewer keeps requesting changes |
| **Telegram delivery** | Message lost | Question marked delivered but not sent |

---

## Test Steps

1. **Reset status.json** to `bootstrap_comms` phase
2. **Start bot** in background (you already have it running)
3. **Run `/orchestrator`** - I'll execute each phase carefully
4. **Document any issues** as they occur
5. **You answer questions** on Telegram when they arrive

---

## Success Criteria

- [ ] Workflow completes to `done` phase
- [ ] At least one real Telegram question/answer exchange
- [ ] GPT suggestions working (the actual fix)
- [ ] No manual intervention needed (except Telegram replies)
- [ ] All artifacts created correctly

---

## Ready?

Say **"go"** to reset status.json and start the workflow.
