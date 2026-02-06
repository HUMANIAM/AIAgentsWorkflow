# Workflow Review: Path Contradictions Found

All 19 workflow files reference `agent_runtime/artifacts_history/` but the actual folder is `agent_runtime/docs/`.

## Critical Issue: Path Mismatch

| Workflow References | Actual Path |
|---------------------|-------------|
| `agent_runtime/artifacts_history/` | `agent_runtime/docs/` |
| `agent_runtime/artifacts_history/templates/` | `agent_runtime/docs/templates/` |
| `agent_runtime/artifacts_history/git_protocol.md` | `agent_runtime/docs/git_protocol.md` |
| `agent_runtime/artifacts_history/workflow_protocol.md` | `agent_runtime/docs/workflow_protocol.md` |

**68 occurrences** across 19 workflow files need to be updated.

---

## Files Affected

All workflow files in `.windsurf/workflows/`:
- `system_analyst.md` (9 occurrences)
- `architect.md` (7 occurrences)
- `backend.md` (5 occurrences)
- `orchestrator.md` (5 occurrences)
- `backend_tester.md`, `frontend.md`, `frontend_tester.md`, `integration_tester.md`, `security.md` (4 each)
- All reviewer files (2-3 each)

---

## Proposed Fix

**Option A: Rename folder** (simpler)
```bash
mv agent_runtime/docs agent_runtime/artifacts_history
```

**Option B: Update all workflows** (more work)
- Replace all `artifacts_history` → `docs` in 19 workflow files

---

## Other Observations (No Issues)

✅ **Git protocol** - Correctly references `idea/<idea_id>` branch naming  
✅ **Bot startup** - Orchestrator Step 0 correctly checks for bot process  
✅ **Status.json paths** - Correctly uses `agent_runtime/status.json`  
✅ **Plugin context** - Correctly uses `agent_runtime/plugin/context.md`  
✅ **Forced approval policy** - Max 2 review cycles, consistent across all reviewers  
✅ **Silent execution** - All agents have mandatory silent start  
✅ **Development philosophy** - KISS/DRY/YAGNI/SOLID consistent across all  

---

## Recommendation

**Use Option A** - Rename `agent_runtime/docs` to `agent_runtime/artifacts_history` to match workflow references. This is cleaner because:
1. "artifacts_history" is more descriptive for workflow outputs
2. Only 1 rename vs 68 text replacements
3. Keeps workflows as the source of truth

---

## Action Required

Please confirm which option you prefer:
- **A**: Rename folder `docs` → `artifacts_history`
- **B**: Update all workflow files `artifacts_history` → `docs`
