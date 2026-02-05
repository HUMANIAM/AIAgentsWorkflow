# Acceptance Contract

## AC-01: Telegram Q/A Round-Trip Integration

### Objective
Verify that the steward_ai_zorba_bot successfully completes a full question-answer cycle between AI agents and the client via Telegram, with proper status.json updates.

### Preconditions
- Telegram bot token is configured in `steward_ai_zorba_bot/.env`
- Client user ID is added to `status.json.client_channel.allowed_user_ids`
- Bridge is running and monitoring `status.json`

### Test Steps
1. **Question Injection**
   - Add a test question to `status.json.client_questions[]` with `delivery_status=pending`
   - Include required fields: `id`, `question`, `created_at`, `delivery_status`, `is_answered=false`

2. **Question Delivery Verification**
   - Bridge detects new question within polling interval (≤ 10 seconds)
   - Question is sent to client via Telegram
   - `status.json` shows `delivery_status=sent` and `delivered_at` timestamp

3. **Client Response**
   - Client replies on Telegram using format: `<question_id> = <answer>`
   - Bridge processes the reply and validates user ID

4. **Answer Processing Verification**
   - Answer is appended to `status.json.client_answers[]` with:
     - `question_id`, `answer`, `source="telegram"`, `answered_at` timestamp
   - Original question is marked: `is_answered=true`, `answered_at`, `answered_by="client"`

5. **Audit Trail Validation**
   - All timestamps are present and sequential
   - No data loss or corruption in the round-trip

### Measurable Oracles
- **Delivery Latency**: Question delivery ≤ 10 seconds after injection
- **Response Latency**: Answer processing ≤ 5 seconds after client reply
- **Data Integrity**: 100% of question fields preserved in round-trip
- **Security**: Only messages from allowed user IDs are processed
- **Audit Completeness**: All state changes have valid timestamps

### Success Criteria
- [ ] Question successfully delivered to client via Telegram
- [ ] Client reply correctly parsed and processed
- [ ] status.json properly updated with answer metadata
- [ ] Original question marked as answered
- [ ] All timestamps present and valid
- [ ] No security violations (unauthorized users rejected)

### Failure Modes
- **Telegram Unavailable**: Bridge falls back to `comms.state = "fallback_only"`
- **Invalid Format**: Malformed replies are logged and ignored
- **Unauthorized User**: Messages from unknown users are rejected
- **Network Issues**: Retry logic handles temporary failures

### Evidence Required
- Screenshots of Telegram messages (question and answer)
- status.json content showing before/after states
- Bridge logs showing successful processing
- Integration test report confirming all oracles pass

### Sign-off
- **System Analyst**: Requirements verified
- **Developer**: Implementation complete  
- **DevOps**: CI/CD pipeline validated
- **Client**: Acceptance confirmed
