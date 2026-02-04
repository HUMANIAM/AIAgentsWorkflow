---
doc: decisions
version: 2
owner: architect
purpose: "Record decision rationale (options, trade-offs, validation) as D-IDs."
last_updated: 2026-02-03
---

# Decisions (ADR-lite)

## Rules
- Any non-trivial choice (tools/frameworks/architecture/CI policy/security posture) must be recorded.
- Decisions must be testable: include a validation plan.

## Template
- **ID**: D-YYYYMMDD-###
- **Status**: proposed | accepted | superseded
- **Owner**: <role>
- **Decision**: <one sentence>
- **Context**: <why a decision is needed>
- **Options considered**:
  - A) <option>
  - B) <option>
  - (C) <option>
- **Trade-offs**:
  - Pros:
  - Cons:
  - Risks:
- **Why chosen**: <tie to requirements / AC scenarios>
- **Validation**: <how to measure/verify; tests/benchmarks/CI signals>
- **Impacts**: <what changes because of this decision>
- **Links**: <files, AC-xx IDs, ChangeSet IDs>

---

## Decisions Log
<!-- Append newest decisions at the bottom -->
