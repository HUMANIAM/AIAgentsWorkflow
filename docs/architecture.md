---
doc: architecture
version: 2
owner: architect
last_updated: 2026-02-06
---

# Architecture: fix_gpt_suggestions

## Summary
This is a **dependency-only fix**. No architectural changes required. The existing code is correct; only the package versions in `requirements.txt` needed updating.

## Change Scope

### Modified Files
| File | Change |
|------|--------|
| `steward_ai_zorba_bot/requirements.txt` | Added `httpx==0.27.0` pin |

### No Changes Required
- `services/openai_client.py` - existing code works correctly
- `services/status_handler.py` - no changes
- `apps/telegram/question_poller.py` - no changes
- `apps/telegram/app.py` - no changes

## Root Cause Analysis

```
openai 1.6.1 → requires httpx
python-telegram-bot 21.3 → requires httpx~=0.27

httpx 0.28.1 (auto-installed) → incompatible with openai 1.6.1
  Error: TypeError: __init__() got an unexpected keyword argument 'proxies'

Fix: Pin httpx==0.27.0 → compatible with both packages
```

## Verification Evidence

```python
# Test 1: OpenAI API call
GPT Response: Hello, howdy there!

# Test 2: get_suggestions() function
Suggestions for "What color should the app theme be?":
1. Use a neutral color like blue or gray...
2. Select a color that aligns with our brand guidelines...
3. Let the development team choose...
```

## Decision Log

### D-01: Pin httpx version
- **Decision**: Pin httpx==0.27.0 in requirements.txt
- **Rationale**: Resolves compatibility between openai 1.6.1 and python-telegram-bot 21.3
- **Risk**: Low - both packages support this version
