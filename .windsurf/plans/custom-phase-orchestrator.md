# Custom Phase Orchestrator

Add ability to run `/orchestrator <phase1>, <phase2>, ...` to execute only specified phases in order, then stop.

---

## Current Behavior
- `/orchestrator` runs all phases from current position to `done`
- No way to run specific phases only

## Proposed Behavior
- `/orchestrator backend, frontend, integration_testing` → runs only those 3 phases in order
- Sets `status.json` to first phase, executes it, then next, then stops after last specified phase
- Skips phases not in the list

---

## Implementation

### 1. Update orchestrator.md workflow

Add new section after "HARD START ALGORITHM":

```markdown
## Custom Phase Mode

If `/orchestrator <phases>` is invoked with comma-separated phase names:

### Step A2: Parse Custom Phases
1. Parse phases from command: `backend, frontend, integration_testing`
2. Validate each phase exists in PHASES list
3. Store as `custom_phases` array

### Step B2: Custom Phase Logic
- Set `current_phase` to first phase in `custom_phases`
- Execute phase (owner → reviewer)
- On completion, advance to next phase in `custom_phases`
- When last phase completes → STOP (do not advance to `done`)

### Phase Names (valid values)
- bootstrap_comms
- requirements
- architecture
- devops
- backend
- backend_testing
- frontend
- frontend_testing
- integration_testing
- security
- client_acceptance
```

### 2. Example Usage

```
/orchestrator backend, frontend, integration_testing
```

This will:
1. Set `current_phase: "backend"`, execute backend → backend_reviewer
2. Set `current_phase: "frontend"`, execute frontend → frontend_reviewer
3. Set `current_phase: "integration_testing"`, execute integration_tester → integration_tester_reviewer
4. STOP (not advance to security or done)

---

## Status.json Changes

Add optional field to track custom mode:
```json
{
  "custom_phases": ["backend", "frontend", "integration_testing"],
  "custom_phase_index": 0
}
```

When `custom_phases` is set:
- Orchestrator uses this list instead of default phase order
- Clears `custom_phases` when complete

---

## Ready?

Say **"go"** to implement this change to the orchestrator workflow.
