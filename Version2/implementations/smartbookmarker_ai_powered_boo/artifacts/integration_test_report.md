# Integration Test Report

- Generated: `2026-02-08T19:13:00Z`
- Scope: extension/backend communication + Google Sheets tab write/read verification
- Result: `PASS`

## Remediation Applied
- Root cause found: runtime environment was missing Google client libraries, so saves fell back to `mock_sheet`.
- Fix applied in runtime: installed `google-auth` and `google-api-python-client` into project `.venv`.
- Persistence fix applied: added both dependencies to `agent_runtime/steward_ai_zorba_bot/requirements.txt`.

## Test 1: Live Google Sheets Roundtrip via Backend API
- Method:
  - Read initial row count from tab `research`.
  - Send `POST /api/save` (simulating extension save).
  - Send `GET /api/notes?category=research`.
  - Read row count again from Google tab `research`.
- Evidence:
  - `google_rows_before: 2`
  - `google_rows_after: 3`
  - `google_rows_delta: 1`
  - `api_save_ok: True`
  - `api_save_storage_mode: google_sheets`
  - `api_save_destination: google_sheets:research`
  - `api_notes_last_text_prefix: Integration extension->backend->google probe ...`

## Test 2: Simulated Extension E2E
- Command: `python tests/e2e/simulated_playwright.py`
- Result: `PASS`
- Evidence:
  - `POST /api/save` returned `200`
  - `GET /api/notes?category=research` returned `200`

## Test 3: Backend Roundtrip Smoke
- Result: `PASS`
- Evidence:
  - `backend_roundtrip_check: PASS`
  - `backend_roundtrip_storage_mode: google_sheets`

## Notes
- The current `GET /api/notes` endpoint returns notes from workspace storage (`backend/data/notes.json`), not directly from Google Sheets.
- Google Sheets communication for write path is confirmed working in this run.
