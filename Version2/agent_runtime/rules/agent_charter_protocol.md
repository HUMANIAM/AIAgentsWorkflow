# Agent Charter Protocol

## Purpose
Define mandatory structure for role workflow charter files.

## Mandatory sections
Each charter in `.windseruf/workflows/*.md` must include:
1. Authority
2. Non-Authority
3. Required Inputs
4. Required Outputs
5. Quality Gates
6. Failure Policy
7. Handoff Packet Requirements
8. Definition of Done

## Compliance rule
A role charter is invalid if any mandatory section is missing.

## Versioning
Each charter frontmatter must include:
- `role`
- `charter_version`
- `profile_scope`
- `mission`
