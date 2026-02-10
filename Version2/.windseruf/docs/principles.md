# Principles

## 1) Human first, agent accelerated
Agents are execution partners. The human engineer remains accountable for intent, decisions, and release.

## 2) State over chat
All workflow truth lives in `agent_runtime/status.json`, not transient conversation.

## 3) Evidence over claims
No phase is complete without objective evidence tied to acceptance criteria IDs.

## 4) Deterministic blocking
Workflow blocking is computed from unresolved required questions and pending governance gates.

## 5) Minimal ceremony
Use gates only when risk justifies them. Normal clarification Q/A is not a governance gate.

## 6) Small slices
Work in AC-mapped slices with short feedback loops and frequent validation.

## 7) Explicit tradeoffs
Major choices require a decision record with options, risks, and rollback path.

## 8) Post-release learning
Every release updates the AI evaluation baseline and reliability runbook.
