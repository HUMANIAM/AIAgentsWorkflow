#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "notes.json"
MOCK_SHEET_DIR = DATA_DIR / "mock_sheet"
DEFAULT_CATEGORIES = ["research", "engineering", "product", "inbox"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_json_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")


def _read_workspace_env() -> Dict[str, str]:
    env_path = WORKSPACE_ROOT / ".env"
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


_ENV_FILE_CACHE = _read_workspace_env()


def _env(key: str, default: str = "") -> str:
    runtime_value = os.getenv(key, "").strip()
    if runtime_value:
        return runtime_value
    return _ENV_FILE_CACHE.get(key, default)


def _safe_tab(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "inbox"


def _keyword_category(text: str) -> str:
    lowered = (text or "").lower()
    if any(token in lowered for token in ["bug", "fix", "error", "exception", "traceback"]):
        return "engineering"
    if any(token in lowered for token in ["book", "article", "read", "paper", "research"]):
        return "research"
    if any(token in lowered for token in ["roadmap", "feature", "release", "customer", "product"]):
        return "product"
    return "inbox"


def _clean_json_payload(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = [line for line in raw.splitlines() if not line.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _llm_classify(text: str, categories: List[str]) -> Tuple[Optional[str], Optional[str]]:
    enabled = _env("SMARTBOOKMARKER_LLM_ENABLED", "0").lower() in {"1", "true", "yes"}
    api_key = _env("AI_API_KEY", "")
    if not enabled or not api_key:
        return None, None

    model = _env("SMARTBOOKMARKER_MODEL", "gpt-4o-mini")
    prompt = (
        "You categorize selected browser text for SmartBookmarker. "
        "Return strict JSON with keys category and headline. "
        f"Category must be one of: {', '.join(categories)}."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = _clean_json_payload(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, error.URLError, error.HTTPError, TimeoutError):
        return None, None

    category = str(parsed.get("category", "")).strip().lower()
    headline = str(parsed.get("headline", "")).strip()
    if category not in categories:
        category = ""
    return (category or None), (headline or None)


def generate_headline(text: str, categories: Optional[List[str]] = None) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return "Untitled note"

    categories = categories or DEFAULT_CATEGORIES
    _cat, llm_headline = _llm_classify(cleaned, categories)
    if llm_headline:
        return llm_headline[:90]

    words = cleaned.split()
    if len(words) <= 10:
        return cleaned[:90]
    return (" ".join(words[:10]) + "...")[:90]


def categorize_text(text: str, categories: Optional[List[str]] = None) -> str:
    categories = categories or DEFAULT_CATEGORIES
    llm_category, _headline = _llm_classify(text, categories)
    if llm_category:
        return _safe_tab(llm_category)
    return _keyword_category(text)


def _format_note_block(note: Dict[str, str]) -> str:
    return (
        "-----\n"
        f"# {note['headline']}\n"
        f"created_at: {note['created_at']}\n"
        f"category: {note['category']}\n\n"
        f"{note['text']}\n"
        "-----\n"
    )


def _resolve_credentials_path(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate
    return (WORKSPACE_ROOT / candidate).resolve()


def _try_google_sheets_write(category: str, block: str) -> Tuple[bool, str]:
    spreadsheet_id = _env("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    credentials_value = _env("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not spreadsheet_id or not credentials_value:
        return False, "google_missing_config"

    credentials_path = _resolve_credentials_path(credentials_value)
    if not credentials_path.exists():
        return False, "google_credentials_not_found"

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception:
        return False, "google_libs_unavailable"

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties.title",
        ).execute()
        titles = {
            str(item.get("properties", {}).get("title", ""))
            for item in meta.get("sheets", [])
            if isinstance(item, dict)
        }
        if category not in titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": category}}}]},
            ).execute()
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{category}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[block]]},
        ).execute()
        return True, f"google_sheets:{category}"
    except Exception as exc:
        return False, f"google_write_failed:{exc.__class__.__name__}"


def _write_mock_sheet(category: str, block: str, sheet_dir: Path = MOCK_SHEET_DIR) -> str:
    sheet_dir.mkdir(parents=True, exist_ok=True)
    tab_file = sheet_dir / f"{_safe_tab(category)}.md"
    with tab_file.open("a", encoding="utf-8") as handle:
        handle.write(block + "\n")
    return str(tab_file)


def save_note(
    note_text: str,
    category: Optional[str] = None,
    path: Path = DATA_FILE,
    sheet_dir: Path = MOCK_SHEET_DIR,
) -> Dict[str, str]:
    _ensure_json_file(path)
    payload: List[Dict[str, str]] = json.loads(path.read_text(encoding="utf-8"))
    cleaned_text = (note_text or "").strip()
    categories = list(DEFAULT_CATEGORIES)
    selected_category = _safe_tab(category) if category else categorize_text(cleaned_text, categories)
    note = {
        "headline": generate_headline(cleaned_text, categories),
        "text": cleaned_text,
        "category": selected_category,
        "created_at": _utc_now(),
    }
    block = _format_note_block(note)
    saved_to_google, destination = _try_google_sheets_write(selected_category, block)
    if saved_to_google:
        note["storage_mode"] = "google_sheets"
    else:
        note["storage_mode"] = "mock_sheet"
        destination = _write_mock_sheet(selected_category, block, sheet_dir=sheet_dir)
    note["destination"] = destination

    payload.append(note)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return note


def retrieve_notes(category: Optional[str] = None, path: Path = DATA_FILE) -> List[Dict[str, str]]:
    _ensure_json_file(path)
    payload: List[Dict[str, str]] = json.loads(path.read_text(encoding="utf-8"))
    if not category:
        return payload
    normalized = _safe_tab(category)
    return [item for item in payload if _safe_tab(str(item.get("category", ""))) == normalized]


def ingest_selection(
    selected_text: str,
    category_override: Optional[str] = None,
    path: Path = DATA_FILE,
    sheet_dir: Path = MOCK_SHEET_DIR,
) -> Dict[str, str]:
    return save_note(
        note_text=selected_text,
        category=category_override,
        path=path,
        sheet_dir=sheet_dir,
    )
