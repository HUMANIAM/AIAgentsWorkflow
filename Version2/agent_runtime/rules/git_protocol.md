---
doc: git_protocol
version: 2
owner: orchestrator
purpose: "Enforce small, role-scoped commits with verifiable evidence in realization mode."
last_updated: 2026-02-08
---

# Git Protocol (Version2 Realization)

## Scope
This protocol is mandatory for `execution_mode=realization`.

## Hard Rules
1. Every non-gate role step must produce at least one new commit.
2. Commit subject must match:
   - ``<type>(<role>): <intent>``
3. `<role>` in commit subject must match the active workflow role.
4. Commits must remain local to the workspace repository unless explicitly released by human approval.

## Allowed commit types
- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `style`
- `chore`
- `security`
- `review`

## Enforcement
The orchestrator blocks transition when:
1. No new commit is detected for the current role step.
2. Commit subject does not match protocol pattern.
3. Commit role scope does not match current role.

## Evidence
All role-step commits must be recorded in:
- `agent_runtime/artifacts/<idea_slug>/10_commit_ledger.md`

Each entry includes:
1. timestamp
2. role
3. step_id
4. commit_sha
5. commit message
