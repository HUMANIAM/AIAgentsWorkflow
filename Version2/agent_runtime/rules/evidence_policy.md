# Evidence Policy

## Evidence standard
Any completion claim must attach verifiable evidence.

## Minimum evidence by area
- Requirements: measurable AC and oracle mapping.
- Reviewer phases: review report with verdict and actionable findings.
- Build: code diff + test execution results.
- QA: AC pass/fail matrix.
- Security: findings with severity and proof.
- Reliability: health checks and recovery verification.
- AI evaluation: benchmark scores and regression delta.

## Evidence quality checks
- Timestamped.
- Reproducible command or method.
- Linked to AC IDs or decision IDs.
- Includes failure evidence when applicable.
- Stored under per-idea runtime path:
  - `agent_runtime/artifacts/<idea_headline_slug>/`
- Realization mode must include git evidence:
  - `10_commit_ledger.md` with role-step commit SHA and message.

## Reject conditions
- Claim without evidence.
- Subjective pass criteria.
- Missing mapping to AC IDs.
