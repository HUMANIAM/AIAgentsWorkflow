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

### D-20260205-001
- **Status**: accepted
- **Owner**: devops
- **Decision**: Use Makefile for local CI entrypoints and GitHub Actions for CI/CD
- **Context**: Need standardized CI/CD pipeline that works locally and in CI
- **Options considered**:
  - A) Makefile + GitHub Actions
  - B) Taskfile + GitHub Actions  
  - C) Shell scripts + GitHub Actions
- **Trade-offs**:
  - Pros:
    - Makefile is universally available, simple syntax
    - GitHub Actions provides free CI/CD with good Python support
    - Consistent commands between local and CI
  - Cons:
    - Make has some quirks with indentation
    - GitHub Actions has YAML complexity
  - Risks:
    - Make version compatibility issues (minimal risk)
    - GitHub Actions workflow changes could break CI
- **Why chosen**: Makefile is the simplest, most portable solution that meets the workflow requirement for "Makefile (recommended)"
- **Validation**: `make check` runs successfully locally and GitHub Actions workflow passes on PR
- **Impacts**: 
  - Added Makefile with standard targets (check, test, lint, format, etc.)
  - Added .github/workflows/ci.yml with comprehensive checks
  - Updated docs/runbook.md to reference Makefile targets
- **Links**: Makefile, .github/workflows/ci.yml, docs/runbook.md

### D-20260205-002
- **Status**: accepted
- **Owner**: devops
- **Decision**: Use ruff, black, mypy, bandit, pytest for Python toolchain
- **Context**: Need comprehensive Python code quality and security tooling
- **Options considered**:
  - A) ruff + black + mypy + bandit + pytest (chosen)
  - B) pylint + black + mypy + safety + pytest
  - C) flake8 + black + mypy + bandit + pytest
- **Trade-offs**:
  - Pros:
    - ruff is extremely fast (written in Rust)
    - black is the de-facto standard for Python formatting
    - mypy provides static type checking
    - bandit focuses on security vulnerabilities
    - pytest is the standard testing framework
  - Cons:
    - Multiple tools to maintain
    - Some overlap in functionality
  - Risks:
    - Tool version conflicts
    - False positives/negatives in security scanning
- **Why chosen**: This combination provides comprehensive coverage with industry-standard tools
- **Validation**: All tools run successfully in CI and `make check` passes
- **Impacts**: 
  - Tool dependencies added to Makefile install target
  - CI workflow runs all tools
  - Local development uses same toolchain
- **Links**: Makefile, .github/workflows/ci.yml

### D-20260205-003
- **Status**: accepted
- **Owner**: system_analyst
- **Decision**: Use polling-based architecture instead of webhooks for Telegram integration
- **Context**: Need to choose between webhook and polling approaches for receiving Telegram messages
- **Options considered**:
  - A) Webhook-based (requires public endpoint)
  - B) Polling-based (chosen)
- **Trade-offs**:
  - Pros:
    - Polling is simpler, no public endpoint required
    - Works behind NAT/firewalls without configuration
    - Easier to debug and test locally
    - Consistent with "keep it minimal" requirement
  - Cons:
    - Slightly higher latency than webhooks
    - Continuous API calls (minimal with 5-second polling)
  - Risks:
    - Rate limiting if polling too frequently
    - Higher resource usage than webhooks
- **Why chosen**: Aligns with local-only requirement and simplicity goals
- **Validation**: Bridge successfully receives messages within 10-second polling window
- **Impacts**: 
  - Simpler deployment model
  - No need for public URL or SSL certificates
  - Consistent resource usage pattern
- **Links**: docs/requirements.md (FR-004), plugin/context.md

### D-20260205-004
- **Status**: accepted
- **Owner**: system_analyst
- **Decision**: Use structured JSON format for status.json with explicit schema
- **Context**: Need to define data structure for questions, answers, and metadata
- **Options considered**:
  - A) Simple key-value pairs
  - B) Structured objects with metadata (chosen)
  - C) Separate files per entity
- **Trade-offs**:
  - Pros:
    - Rich metadata enables audit trails and debugging
    - Type safety and validation possible
    - Extensible for future features
    - JSON schema validation available
  - Cons:
    - More complex than simple key-value
    - Larger file size
  - Risks:
    - Schema evolution challenges
    - JSON parsing overhead (minimal)
- **Why chosen**: Enables comprehensive audit trails required by acceptance criteria
- **Validation**: All required fields present in test data and properly validated
- **Impacts**: 
  - Defined schema for client_questions and client_answers arrays
  - Timestamp tracking for all operations
  - Delivery status tracking for questions
- **Links**: docs/acceptance_contract.md (AC-01), status.json structure

### D-20260205-005
- **Status**: accepted
- **Owner**: system_analyst
- **Decision**: Implement fallback communication mode using direct status.json editing
- **Context**: Must ensure workflow continues even if Telegram is unavailable
- **Options considered**:
  - A) Email fallback
  - B) Direct file editing (chosen)
  - C) Multiple messaging services
- **Trade-offs**:
  - Pros:
    - Zero additional dependencies
    - Always available (file system access)
    - Simple to implement and test
    - Consistent with existing workflow
  - Cons:
    - Manual process for client
    - No real-time notifications
  - Risks:
    - Client may forget to check status.json
    - File corruption during editing
- **Why chosen**: Meets "never block workflow" requirement with minimal complexity
- **Validation**: Client can successfully add answers with source="status_file" when comms.state="fallback_only"
- **Impacts**: 
  - Additional communication channel in status.json
  - comms.state field to indicate active mode
  - Source tracking for answers
- **Links**: plugin/context.md (Comms fallback section), docs/requirements.md (FR-003)
