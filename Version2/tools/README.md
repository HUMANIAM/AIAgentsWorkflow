# Version2 Tools Registry

This file is the canonical registry for executable tools in Version2.
Agents and clients should resolve tool paths from this registry instead of hardcoding script locations.

## orchestrator
- entrypoint: `src/orchestrator/main.py`
- purpose: Deterministic SDLC orchestration engine (profile-driven).
- module boundaries:
  - `src/orchestrator/main.py`: CLI surface + command orchestration.
  - `src/orchestrator/state_machine.py`: status transition engine.
  - `src/orchestrator/git_protocol.py`: commit policy enforcement + ledger.
  - `src/orchestrator/validation.py`: schema/profile validation.
  - `src/orchestrator/workspace_bootstrap.py`: realization workspace/bootstrap concerns.
  - deterministic path handling: CLI/status/context/workspace paths are normalized to absolute paths to avoid cwd-dependent behavior.
  - bootstrap idempotency: existing idea-local adapter/readme are preserved on reruns.
- invocation examples:
  - `python Version2/tools/src/orchestrator/main.py list-profiles`
  - `python Version2/tools/src/orchestrator/main.py init '/orchestrator @default_fallback_profile'`
  - `python Version2/tools/src/orchestrator/main.py trigger '/orchestrator'`
- required env vars (optional defaults):
  - `ORCHESTRATOR_PROFILE` (fallback profile if command has no `@profile`)
  - `ORCHESTRATOR_MIDFLOW_HUMAN_GATES`
  - `ORCHESTRATOR_SOURCE_ENV`
  - `ORCHESTRATOR_MAX_STEPS`
  - `AGENT_RUNTIME_DIR`
- I/O contract:
  - input: `Version2/agent_runtime/status.json`, workflow profile, `plugin/context.md`
  - output: updated status, per-idea artifacts, transition trace

## comm_channel_validation
- entrypoint: `comm_channel_validation.py`
- purpose: Communication loop validation utility (manual/offline checks).
