#!/usr/bin/env python3
"""Utility helpers for the Version2 orchestrator tool."""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def artifact_slug_from_status(status: Dict[str, Any]) -> str:
    headline = str(status.get("active_idea_headline", "")).strip()
    idea_id = str(status.get("active_idea_id", "")).strip()
    return slugify(headline) or slugify(idea_id) or "simulation_baseline"


def resolve_artifacts_dir(status: Dict[str, Any], runtime_root: Path) -> Path:
    return runtime_root.resolve() / "artifacts" / artifact_slug_from_status(status)


def resolve_trace_path(
    trace_file_arg: Optional[str],
    status: Dict[str, Any],
    runtime_root: Path,
) -> Path:
    value = (trace_file_arg or "").strip()
    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = runtime_root.resolve() / path
        return path.resolve()
    return (resolve_artifacts_dir(status, runtime_root) / "03_transition_trace.csv").resolve()


def parse_invocation(
    invocation: str,
    *,
    list_profiles_fn: Callable[[], List[str]],
    error_cls: type[Exception],
) -> str:
    invocation = invocation.strip()
    m = re.match(r"^/orchestrator(?:\s+@([a-zA-Z0-9_\-]+))?$", invocation)
    if not m:
        raise error_cls("Invalid invocation. Use `/orchestrator @<profile>`.")
    profile = m.group(1)
    if not profile:
        available = ", ".join(list_profiles_fn()) or "(none)"
        raise error_cls(
            f"No profile provided. Use `/orchestrator @<profile>`. Available profiles: {available}"
        )
    return profile


def parse_trigger_command(
    command: str,
    *,
    default_profile: str,
    error_cls: type[Exception],
) -> str:
    command = command.strip()
    m = re.match(r"^/orchestrator(?:\s+@?([a-zA-Z0-9_\-]+))?$", command)
    if not m:
        raise error_cls(
            "Invalid command. Use `/orchestrator` or `/orchestrator @<profile>`."
        )
    explicit = (m.group(1) or "").strip()
    if explicit:
        return explicit
    return os.getenv("ORCHESTRATOR_PROFILE", default_profile)


def parse_front_matter(text: str) -> Dict[str, str]:
    payload = (text or "").strip()
    if not payload.startswith("---"):
        return {}
    parts = payload.split("\n---", 1)
    if len(parts) != 2:
        return {}
    front: Dict[str, str] = {}
    for line in parts[0].splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        front[key.strip()] = value.strip()
    return front


def resolve_active_idea_id(context_path: Path, *, error_cls: type[Exception]) -> str:
    if not context_path.exists():
        raise error_cls(f"context file not found: {context_path}")
    front = parse_front_matter(context_path.read_text(encoding="utf-8"))
    idea_id = front.get("idea_id", "").strip()
    if not idea_id:
        raise error_cls(
            "Active idea is missing in context front matter (`idea_id`). Activate an idea first."
        )
    return idea_id


def read_idea_headline_and_status(idea_path: Path, *, error_cls: type[Exception]) -> tuple[str, str]:
    if not idea_path.exists():
        raise error_cls(f"idea file not found: {idea_path}")

    headline = ""
    status = ""
    for line in idea_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Headline:**"):
            headline = line.split(":", 1)[1].strip()
        if line.startswith("**Status:**"):
            status = line.split(":", 1)[1].strip().upper()
    return headline, status


def force_idea_status(idea_path: Path, status_value: str) -> None:
    updated = []
    replaced = False
    for line in idea_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Status:**"):
            updated.append(f"**Status:** {status_value}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"**Status:** {status_value}")
    idea_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def parse_midflow_human_gates(raw: str) -> Set[str]:
    tokens = [item.strip().upper() for item in (raw or "").split(",") if item.strip()]
    if not tokens:
        return set()
    if any(token in {"NONE", "NO", "FALSE", "0"} for token in tokens):
        return set()
    return set(tokens)


def human_required_gates() -> Set[str]:
    configured = parse_midflow_human_gates(os.getenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", ""))
    return {"RELEASE_APPROVAL"} | configured


def is_done(status: Dict[str, Any]) -> bool:
    phase = str(status.get("current_phase", "")).lower()
    if phase == "done":
        return True
    plan = status.get("phase_plan", [])
    idx = status.get("current_step_index")
    return isinstance(plan, list) and isinstance(idx, int) and idx >= len(plan)


def find_open_gate_question(status: Dict[str, Any], gate_id: str) -> str:
    for q in status.get("questions", []):
        if not isinstance(q, dict):
            continue
        if str(q.get("gate_id", "")).upper() != gate_id.upper():
            continue
        if q.get("status") in {"pending_delivery", "delivered"}:
            qid = q.get("id")
            if isinstance(qid, str) and qid:
                return qid
    return ""


def ensure_gate_question(
    status: Dict[str, Any],
    gate_id: str,
    step: Dict[str, Any],
    *,
    now_fn: Callable[[], str] = utc_now,
) -> str:
    existing = find_open_gate_question(status, gate_id)
    if existing:
        status["pending_human_question_id"] = existing
        return existing

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    question_id = f"Q-GATE-{gate_id}-{timestamp}"
    created_at = now_fn()
    phase = str(step.get("phase", "unknown"))
    role = str(step.get("role", "human_engineer"))
    idea_id = str(status.get("active_idea_id", "")).strip()
    scope = f" for idea `{idea_id}`" if idea_id else ""
    question_text = (
        f"Approval required for gate `{gate_id}`{scope}. "
        "Reply with `approve`/`yes`/`1` or `reject`/`no`/`2`."
    )

    status.setdefault("questions", []).append(
        {
            "id": question_id,
            "from_role": "orchestrator",
            "to_human": True,
            "required": True,
            "status": "pending_delivery",
            "question": question_text,
            "context": f"phase={phase}, role={role}, gate={gate_id}",
            "created_at": created_at,
            "kind": "governance_gate",
            "gate_id": gate_id,
        }
    )
    status["pending_human_question_id"] = question_id
    return question_id


def append_trace(trace_path: Path, from_status: Dict[str, Any], to_status: Dict[str, Any], result: Any) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    exists = trace_path.exists()
    with trace_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(
                [
                    "timestamp",
                    "profile",
                    "from_step_index",
                    "from_phase",
                    "from_role",
                    "to_step_index",
                    "to_phase",
                    "to_role",
                    "outcome",
                    "message",
                ]
            )
        writer.writerow(
            [
                utc_now(),
                from_status.get("active_profile", ""),
                from_status.get("current_step_index", ""),
                from_status.get("current_phase", ""),
                from_status.get("current_role", ""),
                to_status.get("current_step_index", ""),
                to_status.get("current_phase", ""),
                to_status.get("current_role", ""),
                result.outcome,
                result.message,
            ]
        )
