# Version2 - Human-Centered AI SDLC

This folder contains a fresh SDLC workflow design for human engineers working with AI agents.

Goal:
- Keep the human engineer in control of intent, risk, and release decisions.
- Let agents execute analysis, implementation, testing, and documentation work.
- Keep state deterministic so workflow behavior is explainable and auditable.

## Folder map
- `.windseruf/`: Workflow playbooks and role definitions.
- `agent_runtime/`: Runtime rules, schemas, examples, and templates.
- `tools/`: executable tool registry and tool source code.

## Core idea
This Version2 flow is profile-driven (`/orchestrator @<profile>`), schema-validated, and hard-guarded.
Blocking and routing are derived from structured status state, required outputs, and explicit human gates.

Role execution supports two modes:
- `simulation`: orchestrator impersonates roles and emits deterministic SDLC artifacts.
- `realization`: orchestrator keeps the same hard-guard state machine but delegates step work to the active idea workspace adapter under `Version2/implementations/<idea_id>/adapter/role_adapter.py`.

## Artifact layout
- Runtime artifacts are isolated per active idea:
  - `Version2/agent_runtime/artifacts/<idea_headline_slug>/...`
- Example for SmartBookmarker:
  - `Version2/agent_runtime/artifacts/smartbookmarker_ai_powered_bookmark_organizer/`
- This keeps trace/evidence clean across idea runs.

## Human ownership model
The human engineer owns:
1. Problem framing and success criteria.
2. Scope and priority changes.
3. High-risk architecture/security tradeoffs.
4. Final release approval.

Agents own:
1. Drafting options and implementation slices.
2. Producing evidence for each acceptance criterion.
3. Surfacing risks and asking targeted questions.
4. Maintaining traceable state updates.

## Runtime quick start
1. Initialize flow:
   `python Version2/tools/src/orchestrator/main.py init '/orchestrator @default_fallback_profile'`
2. Validate status:
   `python Version2/tools/src/orchestrator/main.py validate-status`
3. Advance one step:
   `python Version2/tools/src/orchestrator/main.py step`

## Autonomous realization trigger
Use the agent command entrypoint:
`python Version2/tools/src/orchestrator/main.py trigger '/orchestrator'`

Behavior:
1. Resolves `idea_id` from `Version2/agent_runtime/plugin/context.md`.
2. Forces idea start state to `ACTIVATED` for this realization run.
3. Runs `init` + `run` against the selected profile.
4. Profile selection order:
   - explicit command `/orchestrator @<profile>`
   - `ORCHESTRATOR_PROFILE` env var
   - fallback `default_fallback_profile`

## Orchestrator module boundaries
- `tools/src/orchestrator/main.py`: CLI and command routing only.
- `tools/src/orchestrator/state_machine.py`: deterministic transition logic and hard guards.
- `tools/src/orchestrator/git_protocol.py`: realization-mode commit enforcement and commit ledger writing.
- `tools/src/orchestrator/role_executor.py`: role step execution adapter.
- `tools/src/orchestrator/workspace_bootstrap.py`: workspace bootstrap and env/secrets provisioning.
