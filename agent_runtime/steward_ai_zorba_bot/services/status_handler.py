#!/usr/bin/env python3
"""Version2 status.json handler (questions/answers only)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.json_io import load_json_dict, save_json_dict
from services.runtime_paths import (
    resolve_agent_runtime_dir,
    resolve_project_root,
    slugify,
    utc_now,
)
from services.tool_registry import resolve_tool_entrypoint


PROJECT_ROOT = resolve_project_root()


STATUS_FILE = resolve_agent_runtime_dir(PROJECT_ROOT) / "status.json"


def _utc_now() -> str:
    return utc_now()


def read_status() -> Dict[str, Any]:
    return load_json_dict(STATUS_FILE)


def write_status(status: Dict[str, Any]) -> None:
    save_json_dict(STATUS_FILE, status)


def _map_question_for_bot(q: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(q)
    item.setdefault("from_agent", q.get("from_role", "team"))
    item.setdefault("text", q.get("question", ""))
    return item


def get_pending_questions() -> List[Dict[str, Any]]:
    status = read_status()
    questions = status.get("questions", [])
    return [
        _map_question_for_bot(q)
        for q in questions
        if isinstance(q, dict) and q.get("status") == "pending_delivery"
    ]


def get_delivered_questions() -> List[Dict[str, Any]]:
    status = read_status()
    questions = status.get("questions", [])
    return [
        _map_question_for_bot(q)
        for q in questions
        if isinstance(q, dict) and q.get("status") == "delivered"
    ]


def _has_pending_or_delivered_questions(status: Dict[str, Any]) -> bool:
    return any(
        isinstance(q, dict) and q.get("status") in {"pending_delivery", "delivered"}
        for q in status.get("questions", [])
    )


def mark_question_delivered(question_id: str) -> None:
    status = read_status()
    delivered_at = _utc_now()
    for q in status.get("questions", []):
        if isinstance(q, dict) and q.get("id") == question_id:
            q["status"] = "delivered"
            q["delivered_at"] = delivered_at
            break
    write_status(status)


def write_answer(question_id: str, answer: str, source: str = "telegram") -> None:
    status = read_status()
    for q in status.get("questions", []):
        if isinstance(q, dict) and q.get("id") == question_id:
            q["status"] = "answered"
            break
    status.setdefault("answers", [])
    status["answers"].append(
        {
            "question_id": question_id,
            "answer": answer,
            "source": source,
            "answered_at": _utc_now(),
        }
    )
    write_status(status)


def _extract_gate_id(question: Dict[str, Any], question_id: str) -> str:
    gate_id = str(question.get("gate_id", "")).strip()
    if gate_id:
        return gate_id.upper()
    match = re.match(r"^Q-GATE-([A-Z0-9_\\-]+)-\d+$", question_id.upper())
    if match:
        return match.group(1)
    return ""


def _find_question(status: Dict[str, Any], question_id: str) -> Optional[Dict[str, Any]]:
    for q in status.get("questions", []):
        if isinstance(q, dict) and q.get("id") == question_id:
            return q
    return None


def _is_gate_question(question: Dict[str, Any], question_id: str) -> bool:
    kind = str(question.get("kind", "")).strip().lower()
    if kind == "governance_gate":
        return True
    if str(question.get("gate_id", "")).strip():
        return True
    return question_id.upper().startswith("Q-GATE-")


def _map_gate_reply(answer: str) -> Optional[str]:
    token = answer.strip().lower()
    if token in {"approve", "approved", "yes", "1"}:
        return "approved"
    if token in {"reject", "rejected", "no", "2"}:
        return "rejected"
    return None


def _set_gate_decision(status: Dict[str, Any], gate_id: str, decision: str, reason: str) -> bool:
    for gate in status.get("governance_gates", []):
        if isinstance(gate, dict) and str(gate.get("id", "")).upper() == gate_id.upper():
            gate["status"] = decision
            gate["reason"] = reason
            gate["updated_at"] = _utc_now()
            return True
    return False


def _resume_orchestrator_run() -> Dict[str, Any]:
    configured_orchestrator = os.getenv("ORCHESTRATOR_SCRIPT", "").strip()
    if configured_orchestrator:
        orchestrator_script = Path(configured_orchestrator)
        if not orchestrator_script.is_absolute():
            orchestrator_script = PROJECT_ROOT / orchestrator_script
    else:
        orchestrator_script, msg = resolve_tool_entrypoint("orchestrator")
        if orchestrator_script is None:
            return {"ok": False, "message": msg}

    if not orchestrator_script.exists():
        return {"ok": False, "message": f"Orchestrator script not found: {orchestrator_script}"}

    configured_trace = os.getenv("ORCHESTRATOR_TRACE_FILE", "").strip()
    if configured_trace:
        trace_file = configured_trace
    else:
        status = read_status()
        headline = str(status.get("active_idea_headline", "")).strip()
        idea_id = str(status.get("active_idea_id", "")).strip()
        slug = slugify(headline) or slugify(idea_id) or "simulation_baseline"
        trace_file = str(STATUS_FILE.parent / "artifacts" / slug / "03_transition_trace.csv")
    max_steps = os.getenv("ORCHESTRATOR_MAX_STEPS", "200").strip() or "200"
    cmd = [
        sys.executable,
        str(orchestrator_script),
        "run",
        "--status-file",
        str(STATUS_FILE),
        "--trace-file",
        trace_file,
        "--max-steps",
        max_steps,
    ]
    run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        detail = (run.stderr or "").strip() or (run.stdout or "").strip() or "unknown orchestrator error"
        return {"ok": False, "message": detail}
    return {"ok": True, "message": (run.stdout or "").strip()}


def handle_gate_answer(question_id: str, answer: str, source: str = "telegram") -> Dict[str, Any]:
    """
    Process governance-gate answer with strict mapping.

    Returns dict:
      handled(bool), accepted(bool), message(str), decision(str|None)
    """
    status = read_status()
    question = _find_question(status, question_id)
    if not question or not _is_gate_question(question, question_id):
        return {"handled": False, "accepted": False, "message": "", "decision": None}

    decision = _map_gate_reply(answer)
    if not decision:
        return {
            "handled": True,
            "accepted": False,
            "message": "Please reply with `approve`/`yes`/`1` or `reject`/`no`/`2`.",
            "decision": None,
        }

    gate_id = _extract_gate_id(question, question_id)
    if not gate_id:
        return {
            "handled": True,
            "accepted": False,
            "message": "Gate decision could not be mapped to a gate id.",
            "decision": None,
        }

    for q in status.get("questions", []):
        if isinstance(q, dict) and q.get("id") == question_id:
            q["status"] = "answered"
            break

    status.setdefault("answers", [])
    status["answers"].append(
        {
            "question_id": question_id,
            "answer": answer.strip(),
            "source": source,
            "answered_at": _utc_now(),
        }
    )
    status["pending_human_question_id"] = ""
    status["pending_human_gate_id"] = gate_id

    if not _set_gate_decision(status, gate_id, decision, f"Client decision via Telegram: {answer.strip()}"):
        write_status(status)
        return {
            "handled": True,
            "accepted": False,
            "message": f"Gate `{gate_id}` not found in status.",
            "decision": None,
        }

    if gate_id == "RELEASE_APPROVAL":
        status["realization_status"] = "approved" if decision == "approved" else "rejected"

    write_status(status)

    idea_id = str(status.get("active_idea_id", "")).strip()
    if decision == "rejected":
        if gate_id == "RELEASE_APPROVAL" and idea_id:
            from services.idea_handler import STATE_WAITING_REALIZATION_APPROVAL, force_set_idea_status

            force_set_idea_status(idea_id, STATE_WAITING_REALIZATION_APPROVAL)
        return {
            "handled": True,
            "accepted": True,
            "message": f"Gate `{gate_id}` marked rejected. Workflow remains blocked.",
            "decision": decision,
        }

    resume = _resume_orchestrator_run()
    if not resume["ok"]:
        return {
            "handled": True,
            "accepted": True,
            "message": f"Gate `{gate_id}` approved, but orchestrator resume failed: {resume['message']}",
            "decision": decision,
        }

    latest = read_status()
    latest_phase = str(latest.get("current_phase", "")).lower()
    latest_realization = str(latest.get("realization_status", "")).lower()
    latest_idea_id = str(latest.get("active_idea_id", "")).strip()

    if latest_idea_id:
        from services.idea_handler import (
            STATE_DONE,
            STATE_EXECUTING,
            STATE_WAITING_REALIZATION_APPROVAL,
            force_set_idea_status,
        )

        if latest_phase == "done" and latest_realization == "completed":
            force_set_idea_status(latest_idea_id, STATE_DONE)
            return {
                "handled": True,
                "accepted": True,
                "message": "Approval accepted. Workflow completed and idea marked DONE.",
                "decision": decision,
            }

        if latest_realization == "waiting_approval":
            force_set_idea_status(latest_idea_id, STATE_WAITING_REALIZATION_APPROVAL)
        else:
            force_set_idea_status(latest_idea_id, STATE_EXECUTING)

    return {
        "handled": True,
        "accepted": True,
        "message": "Approval accepted. Workflow resumed.",
        "decision": decision,
    }


def is_client_action_required() -> bool:
    status = read_status()
    return _has_pending_or_delivered_questions(status)


def get_current_phase() -> str:
    status = read_status()
    return status.get("current_phase", "")


def get_current_actor() -> str:
    status = read_status()
    return status.get("current_actor", "")
