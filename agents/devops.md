---
role: devops
type: owner
mission: Build repeatable dev env, CI gates, runbook, and bootstrap comms implementation.
---

# DevOps (Owner)

## Phase: bootstrap_comms
Deliver:
- docs/comms_bootstrap_report.md with evidence of Q/A loop
- Set status.json.comms.state to ready OR fallback_only

## Phase: devops (CI + entrypoints)
DevOps MUST implement:
- GitHub Actions workflow(s) for PRs to main:
  - lint
  - format-check
  - tests
  - (optional) typecheck
- A single local entrypoint CI also calls:
  - Makefile (recommended): make check, make test
  - or Taskfile/scripts (record decision)
- Update docs/runbook.md to reference only those entrypoints.
- Record tooling decisions in docs/decisions.md (D-...).
