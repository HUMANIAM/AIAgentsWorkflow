# Windsurf Final Project v2 — AI SDLC Pipeline (Closed Loop)

This repo skeleton defines a strict, orchestrated SDLC workflow for an AI agent team.

## Core principles
- **Single entry point:** `/orchestrator` (problem is read from `plugin/context.md`)
- **Strict phases** with **Owner + Reviewer** for every phase
- **Max 2 review cycles** (cycle 0 → cycle 1). If cycle 1 fails, escalate to **client decision**.
- **status.json** is the single source of truth
- **status_history.csv** logs every state change (append-only)
- **ChangeSets** enforce small, reliable progress with traceability and evidence
- **Telegram** is the preferred client transport; **fallback** is manual edits to `status.json` (or chat → agent writes it)

## Start
1) Edit `plugin/context.md` (fill Telegram IDs, pick ChangeSet cap, confirm merge policy).
2) Put secrets in local env (`.env`), never commit real tokens.
3) In Windsurf, run: `/orchestrator`

Windsurf will invoke the orchestrator agent which advances the workflow.
