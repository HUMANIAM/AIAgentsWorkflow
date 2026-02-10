# Steward Bot Refactor Report

## Scope
This refactor targeted `agent_runtime/steward_ai_zorba_bot/` to improve:

- Reusability
- Maintainability
- Readability
- Security
- DRY / YAGNI discipline
- Test confidence for production deployment

Behavioral goal: **no functional regression**.

## Baseline and Validation
- Baseline tests before refactor: passing (`83` tests).
- Tests after refactor: passing (`88` tests).
- Command used:
  - `pytest -q agent_runtime/steward_ai_zorba_bot/tests`

Result: all existing behavior preserved, with additional regression coverage for new shared modules.

## Changes and Why

### 1) Extracted shared runtime/path/time/slug utilities
**New file:** `services/runtime_paths.py`

Added:
- `resolve_project_root()`
- `resolve_agent_runtime_dir(project_root)`
- `utc_now()`
- `utc_today()`
- `slugify(value, max_len=0)`

Why:
- The same root/runtime resolution and slug/timestamp logic was duplicated across multiple services.
- Centralizing this removes drift risk and makes production path behavior deterministic.

Principles:
- DRY: removed repeated implementations.
- Maintainability: one source of truth for runtime path logic.
- Readability: service modules now focus on business flow, not path plumbing.

### 2) Extracted shared JSON I/O helpers with atomic writes
**New file:** `services/json_io.py`

Added:
- `load_json_dict(path)` (enforces object root)
- `save_json_dict(path, data)` (atomic temp-write + replace)

Why:
- JSON read/write was repeated and inconsistent.
- Atomic write lowers corruption risk under crashes/interruption.

Principles:
- Security/Reliability: safer persistence semantics.
- DRY: shared persistence utility.
- Maintainability: consistent JSON handling.

### 3) Refactored `services/idea_handler.py` to use shared utilities
Updated:
- Runtime root/runtime dir resolution now uses `runtime_paths`.
- Idea ID normalization now reuses shared slug helper.
- UTC date/time generation now uses shared helpers.
- Runtime status reads/writes now use helper functions:
  - `_read_status_file()`
  - `_write_status_file()`
- Replaced repeated ad-hoc status JSON parsing with consistent helper usage.

Why:
- This module had mixed concerns and repeated low-level file logic.
- Consolidation reduces edge-case divergence and future bug surface.

Principles:
- DRY: removed local duplicate root/runtime/time/slug logic.
- Maintainability: less repeated exception-handling code.
- Readability: orchestration/idea lifecycle logic is clearer.

### 4) Refactored `services/status_handler.py` to use shared utilities
Updated:
- Runtime root/runtime dir resolution via `runtime_paths`.
- Status JSON I/O via `json_io`.
- Trace slug generation via shared `slugify`.

Why:
- Status handler and idea handler previously implemented parallel but separate utility logic.
- This increased risk of subtle mismatch in path and trace behavior.

Principles:
- DRY: unified utility behavior.
- Maintainability: easier to evolve status format safely.

### 5) Refactored `services/openai_client.py` to reduce duplication and harden UX errors
Updated:
- Runtime root/runtime dir and date/slug logic now reuse shared helpers.
- Sanitized user-facing fallback in `chat_about_idea`:
  - previously returned raw exception text to user
  - now logs exception internally and returns generic retry message.

Why:
- Duplicate runtime/date/slug logic existed here too.
- Avoiding raw exception text in user chat reduces accidental leakage of internal details.

Principles:
- Security: avoids exposing internal error strings directly to user.
- DRY: shared helper reuse.
- Readability: simplified normalization internals.

### 6) Refactored `services/tool_registry.py` to reuse shared root resolver
Updated:
- Removed local project-root resolver; uses shared utility.

Why:
- Keeps path assumptions consistent with other services.

Principles:
- DRY / Maintainability.

### 7) Refactored Telegram message routing in `apps/telegram/app.py`
Updated:
- Extracted duplicated answer-processing branches into helpers:
  - `_reply_with_poller_feedback`
  - `_try_process_question_answer`
  - `_extract_brainstorming_answer_candidate`
- Preserved existing UX semantics for:
  - active-idea answer path
  - non-idea answer path
  - clarification handling

Why:
- Previous method had duplicated control-flow branches that were harder to reason about and maintain.
- Helper extraction reduces “change and pray” risk in message routing.

Principles:
- Readability: simpler branching in `handle_message`.
- Maintainability: reusable, testable helper methods.
- YAGNI: no new feature introduced, only structure cleanup.

### 8) Improved channel loading structure in `main.py`
Updated:
- Replaced dynamic `__import__` usage with `importlib.import_module`.
- Centralized supported channel list in `SUPPORTED_CHANNELS`.
- Converted helper functions to raise explicit exceptions instead of calling `sys.exit` directly.
- `main()` remains responsible for user-facing termination behavior.

Why:
- Cleaner separation of concerns and improved testability.
- Avoids abrupt exits inside utility functions.

Principles:
- Readability and Maintainability.
- YAGNI: no extra abstraction added beyond what is used.

## New Tests Added
1. `tests/test_runtime_paths.py`
- validates slug length behavior.
- validates relative/absolute runtime dir resolution.

2. `tests/test_json_io.py`
- validates non-object JSON rejection.
- validates successful atomic object write/read.

These tests protect the new shared utilities that multiple services now depend on.

## Files Changed

### Added
- `services/runtime_paths.py`
- `services/json_io.py`
- `tests/test_runtime_paths.py`
- `tests/test_json_io.py`
- `steward_refactor.md`

### Updated
- `services/idea_handler.py`
- `services/status_handler.py`
- `services/openai_client.py`
- `services/tool_registry.py`
- `apps/telegram/app.py`
- `main.py`

## Risk Assessment

Low/controlled risk:
- Changes are mostly structural and utility extraction.
- No intentional command contract or state model change.
- Full steward test suite is passing after changes.

Potential watch points in production:
- Environment/runtime path assumptions (now centralized): verify `.env`/`AGENT_RUNTIME_DIR` is correct in deployment.
- OpenAI transient failures now return generic user message (expected).

## Deployment Notes
Before deploying:
1. Ensure dependencies are installed from `requirements.txt`.
2. Validate `.env` values for:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_ALLOWED_USER_IDS`
   - `AGENT_RUNTIME_DIR`
3. Run:
   - `pytest -q agent_runtime/steward_ai_zorba_bot/tests`
4. Smoke test:
   - `/idea` start/stop
   - `/idea plan`, `/idea activate`, `/idea execute`
   - gate approval reply path in Telegram

## Outcome
The steward codebase now has:
- shared runtime and JSON infrastructure,
- reduced duplication across core services,
- cleaner Telegram message routing,
- safer user-facing error handling,
- stronger test coverage for foundational utilities.

This improves confidence for production maintenance and iterative enhancement.
