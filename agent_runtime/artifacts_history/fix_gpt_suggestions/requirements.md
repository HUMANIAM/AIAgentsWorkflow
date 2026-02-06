---
doc: requirements
version: 2
owner: system_analyst
last_updated: 2026-02-06
---

# Requirements: fix_gpt_suggestions

## Problem Statement
The Telegram bot sends generic fallback suggestions instead of AI-generated ones when delivering questions to the client.

## Acceptance Criteria

### AC-01: GPT suggestions generated
When a question is delivered to the client via Telegram, the bot MUST call the OpenAI API to generate context-specific suggestions.

### AC-02: Suggestions are relevant
The generated suggestions MUST be relevant to the question being asked, not generic placeholders.

### AC-03: Fallback on failure
If the OpenAI API call fails (network error, quota exceeded, etc.), the bot MUST fall back to generic suggestions and continue functioning.

### AC-04: No code changes required
The fix is a dependency version issue. The existing code logic is correct; only `requirements.txt` needs updating.

## Technical Requirements

### TR-01: Version compatibility
- openai==1.6.1
- httpx==0.27.0 (pinned for compatibility)
- python-telegram-bot==21.3

### TR-02: API key configuration
- API key stored in `.env` as `AI_API_KEY`
- Key must have available quota/credits

## Decisions

### D-01: Pin httpx version
Pin httpx==0.27.0 to resolve compatibility issue between openai 1.6.1 and httpx 0.28.1.

## Verification
- [x] OpenAI import works
- [x] OpenAI API call returns response
- [x] get_suggestions() returns relevant suggestions
