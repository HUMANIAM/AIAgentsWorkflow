# AI Scoring Policy (Strict)

## Purpose
Convert role-quality claims into evidence-backed scores.

## Score scale
- Range: 0.0 to 10.0
- Confidence bands:
  - >= 8.5: production-ready
  - 7.0 to 8.4: strong with watchlist
  - 5.0 to 6.9: partial reliability
  - < 5.0: not acceptable

## Weighted dimensions
- Evidence quality: 30%
- Correctness: 30%
- Protocol compliance: 20%
- Handoff quality: 20%

## Hard caps
- Critical protocol breach: cap 4.0
- Unresolved critical defect: cap 5.0
- Missing required artifact: cap 3.0

## Recovery bonus
+0.5 if blocking review feedback is corrected in one loop with clean evidence.

## Required outputs
- `agent_runtime/artifacts/ai_eval_report.md`
- `agent_runtime/artifacts/role_scoreboard.json`
- `agent_runtime/artifacts/benchmark_results.md`
