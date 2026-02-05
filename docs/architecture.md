# Architecture Document

## System Overview
`steward_ai_zorba_bot` is a local Telegram bridge that enables bidirectional communication between AI agents and clients through the SDLC pipeline.

## Architecture Components

### Core Components

#### 1. Status Monitor
- **Responsibility**: Watch `status.json` for changes
- **Implementation**: File polling with configurable interval (5 seconds default)
- **Trigger**: Detect new questions or state changes

#### 2. Telegram Bot Interface  
- **Responsibility**: Handle Telegram API communication
- **Implementation**: python-telegram-bot library
- **Features**: 
  - Send questions to allowed users
  - Receive and parse replies
  - Retry logic with exponential backoff

#### 3. Message Processor
- **Responsibility**: Process incoming Telegram messages
- **Implementation**: Format validation and routing
- **Logic**: Parse `<question_id> = <answer>` format

#### 4. Status Updater
- **Responsibility**: Update `status.json` with answers and metadata
- **Implementation**: JSON manipulation with atomic writes
- **Audit**: Full logging of all state changes

### Data Flow

```
status.json (questions) → Status Monitor → Telegram Bot → Client
Client → Telegram Bot → Message Processor → Status Updater → status.json (answers)
```

### Technology Stack

#### Core Technologies
- **Language**: Python 3.12+
- **Runtime**: Linux local machine
- **State Management**: File-based (status.json)

#### Key Libraries
- `python-telegram-bot`: Telegram API integration
- `python-dotenv`: Environment variable management
- `watchdog`: File system monitoring (optional enhancement)

#### Security Layer
- **Authentication**: User ID validation
- **Secrets Management**: .env file (never committed)
- **Input Validation**: Message format verification

## AC Mapping

### AC-01: Telegram Q/A Round-Trip Integration
- **Owner**: Message Processor + Status Updater
- **Verification**: End-to-end test with real Telegram messages
- **Success Criteria**: 100% message delivery and processing

### AC-02: Fallback Communication
- **Owner**: Status Monitor + Status Updater  
- **Verification**: Manual status file editing test
- **Success Criteria**: Seamless operation without Telegram

### AC-03: Security Validation
- **Owner**: Telegram Bot Interface
- **Verification**: User ID rejection test
- **Success Criteria**: Only allowed users can interact

## Decision Records

### D-001: Polling vs File Watching
**Decision**: Use file polling (5-second interval)
**Alternatives**: 
- File system events (watchdog)
- Database triggers
**Rationale**: 
- ✅ Simple and reliable
- ✅ No external dependencies
- ✅ Predictable resource usage
**Risks**: 
- ⚠️ 5-second latency maximum
- ⚠️ Higher CPU usage than events

### D-002: Retry Strategy
**Decision**: Exponential backoff (max 3 retries)
**Alternatives**:
- Fixed retries
- No retries
- Custom retry policy
**Rationale**:
- ✅ Balances reliability with spam prevention
- ✅ Handles temporary network issues
- ✅ Configurable limits
**Risks**:
- ⚠️ Delayed message delivery
- ⚠️ Complex error handling

### D-003: Error Handling Strategy  
**Decision**: Log warning and ignore malformed messages
**Alternatives**:
- Silent ignore
- Error message to user
- Request clarification
**Rationale**:
- ✅ Maintains audit trail
- ✅ Avoids spam loops
- ✅ Simple implementation
**Risks**:
- ⚠️ User may not know message failed
- ⚠️ Debugging information limited

## ChangeSet Plan

### CS-20260205-001: Core Bridge Implementation
1. Basic status monitoring
2. Telegram bot setup
3. Message processing
4. Status updating

### CS-20260205-002: Error Handling & Retry Logic
1. Exponential backoff implementation
2. Error logging
3. Malformed message handling

### CS-20260205-003: Testing & Validation
1. Unit tests for all components
2. Integration tests (AC-01)
3. Security validation tests

## Validation Strategy

### Unit Testing
- Each component tested in isolation
- Mock Telegram API for testing
- Status file manipulation tests

### Integration Testing  
- End-to-end message flow
- Fallback mode testing
- Error scenario testing

### Security Testing
- User ID validation
- Message format validation
- Secret handling verification

## Deployment Architecture

### Local Deployment
- Single Python process
- File-based state management
- Environment variable configuration
- No external services required

### Monitoring
- Log file output
- Status file audit trail
- Error rate tracking

## Scalability Considerations

### Current Limits
- Single client interaction
- File-based state (not distributed)
- Local deployment only

### Future Enhancements
- Multiple client support
- Database backend option
- Distributed deployment
- Web interface fallback
