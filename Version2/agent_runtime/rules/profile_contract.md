# Workflow Profile Contract

## Purpose
Profiles are the single source of truth for executable phase/role sequencing in Version2.

## Canonical location
- Profile files: `agent_runtime/workflow_profiles/*.yaml`
- Profile schema: `agent_runtime/schemas/workflow_profile.schema.json`

## Runtime contract
1. Orchestrator must load and validate profile before execution.
2. Invalid profile or invocation must fail with a friendly error and valid options.
3. Runtime state must bind to exactly one `active_profile`.
4. Phase plan is compiled from profile roles and persisted in `status.json.phase_plan`.
5. Profile defaults (such as `max_review_cycles`) are enforced as hard guards.
6. Profile `execution_mode` controls runtime behavior:
   - `simulation`: artifact-only deterministic execution.
   - `realization`: workspace bootstrap + git protocol + implementation execution.

## Drift prevention
Any role or phase sequencing change must be made in profile YAML first.
