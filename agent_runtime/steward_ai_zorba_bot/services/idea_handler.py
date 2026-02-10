#!/usr/bin/env python3
"""Idea handler - per-idea file storage and workflow state transitions."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from services.json_io import load_json_dict, save_json_dict
from services.runtime_paths import (
    resolve_agent_runtime_dir,
    resolve_project_root,
    slugify,
    utc_now,
    utc_today,
)
from services.tool_registry import resolve_tool_entrypoint


PROJECT_ROOT = resolve_project_root()


AGENT_RUNTIME = resolve_agent_runtime_dir(PROJECT_ROOT)
IDEAS_DIR = AGENT_RUNTIME / "ideas"
PLUGIN_DIR = AGENT_RUNTIME / "plugin"
STATUS_FILE = AGENT_RUNTIME / "status.json"

STATE_NEW = "NEW"
STATE_REFINING = "REFINING"
STATE_REFINED = "REFINED"
STATE_PLANNED = "PLANNED"
STATE_ACTIVATED = "ACTIVATED"
STATE_EXECUTING = "EXECUTING"
STATE_WAITING_REALIZATION_APPROVAL = "WAITING_REALIZATION_APPROVAL"
STATE_DONE = "DONE"

VALID_STATES = [
    STATE_NEW,
    STATE_REFINING,
    STATE_REFINED,
    STATE_PLANNED,
    STATE_ACTIVATED,
    STATE_EXECUTING,
    STATE_WAITING_REALIZATION_APPROVAL,
    STATE_DONE,
]

_active_sessions: Dict[int, str] = {}


def _utc_now() -> str:
    return utc_now()


def normalize_idea_id(value: str) -> str:
    return slugify(value, max_len=60)


def _idea_path(idea_id: str) -> Path:
    return IDEAS_DIR / f"{idea_id}.md"


def idea_exists(idea_id: str) -> bool:
    return _idea_path(idea_id).exists()


def _ensure_dirs() -> None:
    IDEAS_DIR.mkdir(parents=True, exist_ok=True)
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)


def _split_text(text: str) -> List[str]:
    lines = (text or "").splitlines()
    return lines if lines else [""]


def _today_utc() -> str:
    return utc_today()


def _split_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    cleaned = text.strip()
    if not cleaned.startswith("---"):
        return {}, text

    parts = cleaned.split("\n---", 1)
    if len(parts) != 2:
        return {}, text

    front_raw = parts[0]
    body = parts[1].lstrip("\n")
    front: Dict[str, str] = {}
    for line in front_raw.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        front[key.strip()] = value.strip()

    return front, body


def _serialize_front_matter(front: Dict[str, str], body: str) -> str:
    preferred_order = ["plugin", "version", "owner", "last_updated", "idea_id"]
    lines = ["---"]

    used = set()
    for key in preferred_order:
        if key in front:
            lines.append(f"{key}: {front[key]}")
            used.add(key)

    for key, value in front.items():
        if key in used:
            continue
        lines.append(f"{key}: {value}")

    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip()


def _inject_context_idea_id(text: str, idea_id: str) -> str:
    front, body = _split_front_matter(text)
    if not front:
        front = {
            "plugin": "idea",
            "version": "1",
            "owner": "client",
        }
    front["idea_id"] = idea_id
    front["last_updated"] = _today_utc()
    return _serialize_front_matter(front, body)


def _read_context_idea_id(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    front, _body = _split_front_matter(text)
    raw = front.get("idea_id", "").strip()
    if not raw:
        return None
    return normalize_idea_id(raw)


def _parse_idea_file(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return None

    idea: Dict = {
        "id": path.stem,
        "headline": "",
        "owner_user_id": None,
        "created_at": "",
        "updated_at": "",
        "status": STATE_NEW,
        "chat_history": [],
        "runtime_adjustments": [],
        "path": str(path),
    }

    section = "meta"
    current_msg: Optional[Dict[str, str]] = None

    for raw in lines:
        line = raw.rstrip("\n")

        if line.startswith("## ID:"):
            idea["id"] = line.replace("## ID:", "", 1).strip() or path.stem
            continue

        if line == "### Chat History":
            section = "chat"
            current_msg = None
            continue

        if line == "### Runtime Adjustments":
            section = "adjustments"
            current_msg = None
            continue

        if section == "meta":
            if line.startswith("**Headline:**"):
                idea["headline"] = line.replace("**Headline:**", "", 1).strip()
            elif line.startswith("**Owner User ID:**"):
                raw_owner = line.replace("**Owner User ID:**", "", 1).strip()
                try:
                    idea["owner_user_id"] = int(raw_owner)
                except (TypeError, ValueError):
                    idea["owner_user_id"] = None
            elif line.startswith("**Created:**"):
                idea["created_at"] = line.replace("**Created:**", "", 1).strip()
            elif line.startswith("**Updated:**"):
                idea["updated_at"] = line.replace("**Updated:**", "", 1).strip()
            elif line.startswith("**Status:**"):
                state = line.replace("**Status:**", "", 1).strip().upper()
                if state == "IN_PROGRESS":
                    state = STATE_REFINING
                if state in VALID_STATES:
                    idea["status"] = state
            continue

        if section == "chat":
            if line.startswith("**User:**"):
                current_msg = {"role": "user", "content": line.replace("**User:**", "", 1).strip()}
                idea["chat_history"].append(current_msg)
                continue
            if line.startswith("**GPT:**") or line.startswith("**Gpt:**"):
                current_msg = {
                    "role": "gpt",
                    "content": line.replace("**GPT:**", "", 1).replace("**Gpt:**", "", 1).strip(),
                }
                idea["chat_history"].append(current_msg)
                continue
            if current_msg and line.startswith("    "):
                current_msg["content"] += "\n" + line[4:]
                continue
            if current_msg and line.strip():
                current_msg["content"] += "\n" + line.strip()
                continue
            continue

        if section == "adjustments":
            if line.startswith("- [") and "]" in line:
                end = line.find("]")
                ts = line[3:end]
                msg = line[end + 1 :].strip()
                idea["runtime_adjustments"].append({"timestamp": ts, "message": msg})
                continue
            if line.startswith("    ") and idea["runtime_adjustments"]:
                idea["runtime_adjustments"][-1]["message"] += "\n" + line[4:]
                continue

    if not idea["updated_at"]:
        idea["updated_at"] = idea["created_at"] or _utc_now()

    return idea


def _serialize_idea(idea: Dict) -> str:
    lines: List[str] = [
        f"## ID: {idea['id']}",
        f"**Headline:** {idea.get('headline', '').strip()}",
        f"**Owner User ID:** {idea.get('owner_user_id')}",
        f"**Created:** {idea.get('created_at')}",
        f"**Updated:** {idea.get('updated_at')}",
        f"**Status:** {idea.get('status')}",
        "",
        "### Chat History",
    ]

    for msg in idea.get("chat_history", []):
        role = str(msg.get("role", "")).lower()
        label = "User" if role == "user" else "GPT"
        text_lines = _split_text(str(msg.get("content", "")))
        lines.append(f"**{label}:** {text_lines[0]}")
        for extra in text_lines[1:]:
            lines.append(f"    {extra}")

    lines.append("")
    lines.append("### Runtime Adjustments")
    for entry in idea.get("runtime_adjustments", []):
        ts = entry.get("timestamp") or _utc_now()
        msg_lines = _split_text(str(entry.get("message", "")))
        lines.append(f"- [{ts}] {msg_lines[0]}")
        for extra in msg_lines[1:]:
            lines.append(f"    {extra}")

    return "\n".join(lines).rstrip() + "\n"


def _write_idea(idea: Dict) -> None:
    _ensure_dirs()
    idea["updated_at"] = _utc_now()
    path = _idea_path(str(idea["id"]))
    path.write_text(_serialize_idea(idea), encoding="utf-8")


def _load_idea(idea_id: str) -> Optional[Dict]:
    return _parse_idea_file(_idea_path(idea_id))


def _list_all_ideas() -> List[Dict]:
    _ensure_dirs()
    ideas: List[Dict] = []
    for path in sorted(IDEAS_DIR.glob("*.md")):
        item = _parse_idea_file(path)
        if item:
            ideas.append(item)
    ideas.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return ideas


def _require_owner(idea: Dict, owner_user_id: Optional[int]) -> Tuple[bool, str]:
    if owner_user_id is None:
        return True, ""
    if idea.get("owner_user_id") != owner_user_id:
        return False, "Idea belongs to another user."
    return True, ""


def create_idea(user_id: int, idea_id: str, headline: str, initial_status: str = STATE_REFINING) -> Tuple[bool, str]:
    normalized = normalize_idea_id(idea_id)
    if not normalized:
        return False, "Invalid idea ID."
    if initial_status not in VALID_STATES:
        return False, f"Invalid status: {initial_status}"
    if idea_exists(normalized):
        return False, f"Idea already exists: {normalized}"

    now = _utc_now()
    idea = {
        "id": normalized,
        "headline": headline.strip() or normalized,
        "owner_user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "status": initial_status,
        "chat_history": [],
        "runtime_adjustments": [],
    }
    _write_idea(idea)

    if initial_status == STATE_REFINING:
        _active_sessions[user_id] = normalized

    return True, normalized


def start_idea(user_id: int, idea_id: str) -> Tuple[bool, str]:
    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, user_id)
    if not ok:
        return False, msg

    if idea["status"] in {STATE_EXECUTING, STATE_WAITING_REALIZATION_APPROVAL, STATE_DONE}:
        return False, f"Idea cannot be refined from state {idea['status']}."

    idea["status"] = STATE_REFINING
    _write_idea(idea)
    _active_sessions[user_id] = idea["id"]
    return True, idea["id"]


def get_idea(idea_id: str) -> Optional[Dict]:
    idea = _load_idea(idea_id)
    if not idea:
        return None
    _sync_waiting_realization_state(idea)
    return idea


def get_active_idea(user_id: int) -> Optional[str]:
    return _active_sessions.get(user_id)


def restore_active_sessions() -> Dict[int, str]:
    _active_sessions.clear()

    latest_for_owner: Dict[int, Dict[str, str]] = {}
    refinings_by_owner: Dict[int, List[Dict]] = {}

    for idea in _list_all_ideas():
        if idea.get("status") != STATE_REFINING:
            continue
        owner = idea.get("owner_user_id")
        if owner is None:
            continue
        owner = int(owner)
        refinings_by_owner.setdefault(owner, []).append(idea)
        created = idea.get("updated_at") or idea.get("created_at") or ""
        curr = latest_for_owner.get(owner)
        if not curr or created >= curr.get("updated_at", ""):
            latest_for_owner[owner] = {"id": idea["id"], "updated_at": created}

    for owner, ideas in refinings_by_owner.items():
        keep_id = latest_for_owner[owner]["id"]
        for idea in ideas:
            if idea["id"] == keep_id:
                continue
            idea["status"] = STATE_REFINED
            idea.setdefault("runtime_adjustments", []).append(
                {
                    "timestamp": _utc_now(),
                    "message": "Auto-normalized from REFINING to REFINED during restart recovery.",
                }
            )
            _write_idea(idea)

    for owner, meta in latest_for_owner.items():
        _active_sessions[owner] = meta["id"]

    return dict(_active_sessions)


def get_active_sessions() -> Dict[int, str]:
    return dict(_active_sessions)


def get_last_gpt_message(idea_id: str) -> Optional[str]:
    history = get_chat_history(idea_id)
    for msg in reversed(history):
        if msg.get("role") == "gpt":
            return msg.get("content", "").strip()
    return None


def add_message(idea_id: str, role: str, text: str) -> bool:
    idea = _load_idea(idea_id)
    if not idea:
        return False

    norm_role = "gpt" if str(role).lower() in {"gpt", "assistant"} else "user"
    idea.setdefault("chat_history", []).append({"role": norm_role, "content": text.strip()})
    _write_idea(idea)
    return True


def append_runtime_adjustment(idea_id: str, message: str) -> bool:
    idea = _load_idea(idea_id)
    if not idea:
        return False
    idea.setdefault("runtime_adjustments", []).append({"timestamp": _utc_now(), "message": message})
    _write_idea(idea)
    return True


def append_runtime_adjustments(idea_id: str, messages: List[str]) -> bool:
    idea = _load_idea(idea_id)
    if not idea:
        return False
    for message in messages:
        idea.setdefault("runtime_adjustments", []).append({"timestamp": _utc_now(), "message": message})
    _write_idea(idea)
    return True


def get_chat_history(idea_id: str) -> List[Dict[str, str]]:
    idea = _load_idea(idea_id)
    if not idea:
        return []
    return list(idea.get("chat_history", []))


def end_idea(user_id: int) -> Optional[str]:
    idea_id = _active_sessions.pop(user_id, None)
    if not idea_id:
        return None

    idea = _load_idea(idea_id)
    if not idea:
        return idea_id

    if idea.get("status") == STATE_REFINING:
        idea["status"] = STATE_REFINED
        _write_idea(idea)

    return idea_id


def list_ideas(owner_user_id: Optional[int] = None) -> List[Dict]:
    ideas = _list_all_ideas()
    for idea in ideas:
        _sync_waiting_realization_state(idea)

    if owner_user_id is None:
        return ideas
    return [idea for idea in ideas if idea.get("owner_user_id") == owner_user_id]


def list_ideas_by_state(state: str, owner_user_id: Optional[int] = None) -> List[Dict]:
    state_upper = state.upper()
    if state_upper not in VALID_STATES:
        return []
    return [idea for idea in list_ideas(owner_user_id=owner_user_id) if idea.get("status") == state_upper]


def _demote_owner_activated_ideas(owner_user_id: int, keep_idea_id: str) -> None:
    for idea in _list_all_ideas():
        if idea.get("owner_user_id") != owner_user_id:
            continue
        if idea.get("id") == keep_idea_id:
            continue
        if idea.get("status") == STATE_ACTIVATED:
            idea["status"] = STATE_PLANNED
            _write_idea(idea)


def generate_context_file(idea_id: str, context_content: str) -> str:
    _ensure_dirs()
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    context_file.write_text(context_content, encoding="utf-8")
    return str(context_file)


def plan_idea(idea_id: str, context_content: str, owner_user_id: Optional[int] = None) -> Tuple[bool, str]:
    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, owner_user_id)
    if not ok:
        return False, msg

    if idea.get("status") != STATE_REFINED:
        return False, f"Idea must be REFINED to plan. Current status: {idea.get('status')}"

    context_path = generate_context_file(idea_id, context_content)
    idea["status"] = STATE_PLANNED
    _write_idea(idea)
    return True, f"Planned idea: {idea.get('headline')}\nContext file: {context_path}"


def activate_idea(idea_id: str, owner_user_id: Optional[int] = None) -> Tuple[bool, str]:
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    main_context = PLUGIN_DIR / "context.md"

    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, owner_user_id)
    if not ok:
        return False, msg

    if idea.get("status") != STATE_PLANNED:
        return False, f"Idea must be PLANNED to activate. Current status: {idea.get('status')}"

    if not context_file.exists():
        return False, f"Context file not found for `{idea_id}`. Run `/idea plan {idea_id}` first."

    content = context_file.read_text(encoding="utf-8")
    main_context.write_text(_inject_context_idea_id(content, idea_id), encoding="utf-8")

    if isinstance(idea.get("owner_user_id"), int):
        _demote_owner_activated_ideas(int(idea["owner_user_id"]), keep_idea_id=idea_id)

    idea["status"] = STATE_ACTIVATED
    _write_idea(idea)

    return True, f"Activated context for idea: {idea.get('headline')}"


def _is_release_approval_waiting(status: Dict) -> bool:
    gates = status.get("governance_gates", [])
    release_pending = False
    for gate in gates:
        if isinstance(gate, dict) and gate.get("id") == "RELEASE_APPROVAL" and gate.get("status") == "pending":
            release_pending = True
            break

    if not release_pending:
        return False

    current_phase = str(status.get("current_phase", "")).lower()
    phase_status = str(status.get("phase_status", "")).lower()
    current_role = str(status.get("current_role", "")).lower()

    if current_phase == "release" and phase_status == "waiting" and current_role == "human_engineer":
        return True

    blocking = "\n".join(str(x) for x in status.get("blocking_reasons", []))
    return "RELEASE_APPROVAL" in blocking and phase_status == "waiting"


def _read_status_file() -> Optional[Dict]:
    if not STATUS_FILE.exists():
        return None
    try:
        return load_json_dict(STATUS_FILE)
    except Exception:
        return None


def _write_status_file(status: Dict) -> None:
    save_json_dict(STATUS_FILE, status)


def _sync_waiting_realization_state(idea: Dict) -> None:
    if idea.get("status") != STATE_EXECUTING:
        return

    status = _read_status_file()
    if not status:
        return

    if _is_release_approval_waiting(status):
        idea["status"] = STATE_WAITING_REALIZATION_APPROVAL
        _write_idea(idea)


def _sync_state_from_runtime_status(idea: Dict) -> str:
    """Sync idea status from runtime workflow state after execute/resume."""
    status = _read_status_file()
    if not status:
        if idea.get("status") != STATE_EXECUTING:
            idea["status"] = STATE_EXECUTING
            _write_idea(idea)
        return STATE_EXECUTING

    current_phase = str(status.get("current_phase", "")).lower()
    realization_status = str(status.get("realization_status", "")).lower()

    if current_phase == "done" and realization_status == "completed":
        if idea.get("status") != STATE_DONE:
            idea["status"] = STATE_DONE
            _write_idea(idea)
        return STATE_DONE

    if _is_release_approval_waiting(status):
        if idea.get("status") != STATE_WAITING_REALIZATION_APPROVAL:
            idea["status"] = STATE_WAITING_REALIZATION_APPROVAL
            _write_idea(idea)
        return STATE_WAITING_REALIZATION_APPROVAL

    if idea.get("status") != STATE_EXECUTING:
        idea["status"] = STATE_EXECUTING
        _write_idea(idea)
    return STATE_EXECUTING


def force_set_idea_status(idea_id: str, status_value: str, owner_user_id: Optional[int] = None) -> Tuple[bool, str]:
    """Force-set idea lifecycle status (used by orchestration sync flows)."""
    if status_value not in VALID_STATES:
        return False, f"Invalid status: {status_value}"

    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, owner_user_id)
    if not ok:
        return False, msg

    idea["status"] = status_value
    _write_idea(idea)
    return True, f"Idea status set to {status_value}"


def _stamp_active_idea_in_status(idea: Dict, profile: str) -> None:
    """Persist executed idea metadata into status.json for visibility and traceability."""
    status = _read_status_file()
    if not status:
        return

    idea_id = str(idea.get("id", "")).strip()
    headline = str(idea.get("headline", "")).strip()
    owner = idea.get("owner_user_id")
    now = _utc_now()

    status["active_idea_id"] = idea_id
    status["active_idea_headline"] = headline
    status["active_idea"] = {
        "id": idea_id,
        "headline": headline,
        "owner_user_id": owner,
        "context_file": f"plugin/context_{idea_id}.md",
        "executed_at": now,
        "profile": profile,
    }

    _write_status_file(status)


def execute_idea(idea_id: str, owner_user_id: Optional[int] = None) -> Tuple[bool, str]:
    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, owner_user_id)
    if not ok:
        return False, msg

    if idea.get("status") != STATE_ACTIVATED:
        return False, f"Idea must be ACTIVATED before execute. Current status: {idea.get('status')}"

    context_md = PLUGIN_DIR / "context.md"
    active_idea_id = _read_context_idea_id(context_md)
    if not active_idea_id:
        return (
            False,
            "Active context ownership is missing in `plugin/context.md` (`idea_id`). "
            f"Run `/idea activate {idea_id}` first.",
        )
    if active_idea_id != idea_id:
        return (
            False,
            f"Active context belongs to `{active_idea_id}`, not `{idea_id}`. "
            f"Run `/idea activate {idea_id}` first.",
        )

    configured_orchestrator = os.getenv("ORCHESTRATOR_SCRIPT", "").strip()
    if configured_orchestrator:
        orchestrator_script = Path(configured_orchestrator)
        if not orchestrator_script.is_absolute():
            orchestrator_script = PROJECT_ROOT / orchestrator_script
    else:
        orchestrator_script, msg = resolve_tool_entrypoint("orchestrator")
        if orchestrator_script is None:
            return False, msg

    profile = os.getenv("ORCHESTRATOR_PROFILE", "default_fallback_profile")
    charter_version = os.getenv("ORCHESTRATOR_CHARTER_VERSION", "v2.1")
    headline_slug = normalize_idea_id(str(idea.get("headline", ""))) or idea_id
    default_trace = STATUS_FILE.parent / "artifacts" / headline_slug / "03_transition_trace.csv"
    trace_file = os.getenv(
        "ORCHESTRATOR_TRACE_FILE",
        str(default_trace),
    )
    max_steps_raw = os.getenv("ORCHESTRATOR_MAX_STEPS", "200").strip() or "200"

    if not orchestrator_script.exists():
        return False, f"Orchestrator script not found: {orchestrator_script}"

    init_cmd = [
        sys.executable,
        str(orchestrator_script),
        "init",
        f"/orchestrator @{profile}",
        "--status-file",
        str(STATUS_FILE),
        "--charter-version",
        charter_version,
        "--idea-id",
        idea_id,
        "--idea-headline",
        str(idea.get("headline", "")),
    ]
    init_run = subprocess.run(init_cmd, capture_output=True, text=True, check=False)
    if init_run.returncode != 0:
        stderr = (init_run.stderr or "").strip()
        stdout = (init_run.stdout or "").strip()
        detail = stderr or stdout or "unknown orchestrator error"
        return False, f"Failed to execute orchestrator: {detail}"

    _stamp_active_idea_in_status(idea, profile=profile)

    run_cmd = [
        sys.executable,
        str(orchestrator_script),
        "run",
        "--status-file",
        str(STATUS_FILE),
        "--trace-file",
        trace_file,
        "--max-steps",
        max_steps_raw,
    ]
    run_exec = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
    if run_exec.returncode != 0:
        stderr = (run_exec.stderr or "").strip()
        stdout = (run_exec.stdout or "").strip()
        detail = stderr or stdout or "unknown orchestrator error"
        return False, f"Failed to execute orchestrator run: {detail}"

    synced_state = _sync_state_from_runtime_status(idea)
    _stamp_active_idea_in_status(idea, profile=profile)

    init_output = (init_run.stdout or "").strip()
    run_output = (run_exec.stdout or "").strip()
    combined = "\n".join(part for part in [init_output, run_output] if part).strip()

    if synced_state == STATE_WAITING_REALIZATION_APPROVAL:
        combined += "\nAwaiting RELEASE_APPROVAL response from client."
    elif synced_state == STATE_DONE:
        combined += "\nWorkflow reached completed realization state."

    return True, combined or f"Execution started with profile `{profile}`."


def complete_idea(idea_id: str, owner_user_id: Optional[int] = None) -> Tuple[bool, str]:
    idea = _load_idea(idea_id)
    if not idea:
        return False, f"Idea not found: {idea_id}"

    ok, msg = _require_owner(idea, owner_user_id)
    if not ok:
        return False, msg

    _sync_waiting_realization_state(idea)
    idea = _load_idea(idea_id) or idea

    if idea.get("status") != STATE_WAITING_REALIZATION_APPROVAL:
        return (
            False,
            "Idea must be WAITING_REALIZATION_APPROVAL before done. "
            f"Current status: {idea.get('status')}",
        )

    idea["status"] = STATE_DONE
    _write_idea(idea)
    return True, f"Completed idea: {idea.get('headline')}"
