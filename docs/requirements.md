# Requirements Document

## Overview
Build `steward_ai_zorba_bot`: a local Telegram bridge that enables bidirectional communication between AI agents and clients through the SDLC pipeline.

## Functional Requirements

### FR-001: Question Delivery
- The bridge SHALL monitor `status.json.client_questions[]` for new questions
- For each question with `delivery_status=pending`, the bridge SHALL:
  - Send the question via Telegram to the allowed user
  - Update `delivery_status=sent` and set `delivered_at` timestamp
  - Use the configured Telegram bot token and user IDs

### FR-002: Answer Processing  
- The bridge SHALL monitor Telegram messages from allowed users
- For messages matching format `<question_id> = <answer>`:
  - Append answer to `status.json.client_answers[]` with metadata
  - Mark corresponding question as answered (`is_answered=true`)
  - Set `answered_at` timestamp and `answered_by="client"`
- The bridge SHALL only process messages from allowed user IDs

### FR-003: Fallback Communication
- If Telegram is unavailable, the bridge SHALL set `comms.state = "fallback_only"`
- Clients SHALL be able to add answers directly to `status.json.client_answers[]` with `source="status_file"`
- The bridge SHALL continue normal operation in fallback mode

### FR-004: Status Monitoring
- The bridge SHALL continuously watch `status.json` for changes
- Polling interval SHALL be configurable (default: 5 seconds)
- The bridge SHALL maintain audit trails for all operations

## Non-Functional Requirements

### NFR-001: Security
- Secrets (TELEGRAM_BOT_TOKEN) SHALL NEVER be committed to repository
- The bridge SHALL only accept messages from pre-approved user IDs
- Environment variables SHALL be loaded from `.env` file in `steward_ai_zorba_bot/`

### NFR-002: Reliability
- The bridge SHALL implement retry logic for failed Telegram deliveries
- Failed operations SHALL be logged with appropriate error levels
- The bridge SHALL handle network interruptions gracefully

### NFR-003: Performance
- Polling overhead SHALL be minimal (< 1% CPU usage)
- Message delivery latency SHALL be < 10 seconds under normal conditions
- Memory usage SHALL remain constant during operation

### NFR-004: Maintainability
- Code SHALL be written in Python 3.12+
- The bridge SHALL run on Linux local machines
- No external server hosting SHALL be required
- Logging SHALL be comprehensive but not excessive

## Constraints

### C-001: Technology Stack
- Language: Python 3.12+
- Runtime: Linux local machine
- No databases required (file-based state management)

### C-002: Operational
- No direct pushes to `main` branch (PR-only workflow)
- CI/CD pipeline SHALL pass before merges
- ChangeSet policy SHALL be followed (CS-YYYYMMDD-###)

### C-003: Scope
- Focus ONLY on Telegram bridge functionality
- No unrelated product features
- Minimal viable implementation preferred

## Acceptance Criteria
See `docs/acceptance_contract.md` for detailed acceptance criteria with measurable oracles.

## Dependencies
- Telegram Bot API access
- Valid bot token and user configuration
- Python environment with required packages
