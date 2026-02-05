#!/usr/bin/env python3
"""
Workflow Orchestrator Helper

This repo's "agents" coordinate via status.json. The orchestrator is responsible for
advancing phases and triggering the next agent (owner/reviewer) at the right time.

This script provides deterministic helpers to:
- validate status.json shape
- reconcile obvious inconsistencies (e.g. gates vs comms/ACKs)
- compute/perform the next orchestrator transition

It intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PHASES: List[str] = [
    "bootstrap_comms",
    "requirements",
    "architecture",
    "devops",
    "backend",
    "backend_testing",
    "frontend",
    "frontend_testing",
    "integration_testing",
    "security",
    "client_acceptance",
    "done",
]


PHASE_ACTORS: Dict[str, Tuple[str, Optional[str]]] = {
    "bootstrap_comms": ("devops", "devops_reviewer"),
    "requirements": ("system_analyst", "system_analyst_reviewer"),
    "architecture": ("architect", "architect_reviewer"),
    "devops": ("devops", "devops_reviewer"),
    "backend": ("backend", "backend_reviewer"),
    "backend_testing": ("backend_tester", "backend_tester_reviewer"),
    "frontend": ("frontend", "frontend_reviewer"),
    "frontend_testing": ("frontend_tester", "frontend_tester_reviewer"),
    "integration_testing": ("integration_tester", "integration_tester_reviewer"),
    "security": ("security", "security_reviewer"),
    "client_acceptance": ("client", None),
    "done": ("orchestrator", None),
}


STATUS_REQUIRED_KEYS = [
    "problem",
    "cycle",
    "current_phase",
    "current_actor",
    "phase_status",
    "actor_status",
    "review_status",
    "comms",
    "client_action_required",
    "client_channel",
    "client_questions",
    "client_answers",
    "ack_requests",
    "changesets",
    "artifacts",
    "gates",
    "timestamps",
]


HISTORY_HEADER = [
    "timestamp",
    "from_phase",
    "from_phase_status",
    "from_actor",
    "to_phase",
    "to_actor",
    "to_phase_status",
]


GATE_BY_SIGNAL: Dict[str, str] = {
    "COMMS_READY": "bootstrap_comms",
    "REQ_REVIEW_APPROVED": "requirements",
    "REQ_CLIENT_ACK": "requirements",
    "ARCH_REVIEW_APPROVED": "architecture",
    "DEVOPS_REVIEW_APPROVED": "devops",
    "SECURITY_APPROVED": "security",
    "FINAL_CLIENT_ACK": "client_acceptance",
}


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # "error" | "warning"
    message: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("status.json must be a JSON object")
    return data


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    tmp_path.replace(path)


def validate_status(status: Dict[str, Any]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    for key in STATUS_REQUIRED_KEYS:
        if key not in status:
            issues.append(ValidationIssue("error", f"Missing required key: {key}"))

    # Structural checks (only if keys exist)
    if "cycle" in status and not isinstance(status["cycle"], int):
        issues.append(ValidationIssue("error", "cycle must be an int"))

    for key in ["current_phase", "current_actor", "phase_status", "actor_status", "review_status"]:
        if key in status and not isinstance(status[key], str):
            issues.append(ValidationIssue("error", f"{key} must be a string"))

    for key in ["comms", "client_channel", "changesets", "artifacts", "gates", "timestamps"]:
        if key in status and not isinstance(status[key], dict):
            issues.append(ValidationIssue("error", f"{key} must be an object"))

    for key in ["client_questions", "client_answers", "ack_requests"]:
        if key in status and not isinstance(status[key], list):
            issues.append(ValidationIssue("error", f"{key} must be an array"))

    # Semantic-ish checks (warnings)
    phase = status.get("current_phase")
    if isinstance(phase, str) and phase and phase not in PHASES:
        issues.append(
            ValidationIssue(
                "warning",
                f"current_phase '{phase}' is not a canonical phase. Expected one of: {', '.join(PHASES)}",
            )
        )

    comms_state = status.get("comms", {}).get("state") if isinstance(status.get("comms"), dict) else None
    gates = status.get("gates") if isinstance(status.get("gates"), dict) else {}
    if comms_state in {"ready", "fallback_only"} and gates.get("COMMS_READY") == "pending":
        issues.append(
            ValidationIssue(
                "warning",
                "comms.state is ready/fallback_only but gates.COMMS_READY is still pending",
            )
        )

    if phase == "done" and status.get("phase_status") == "completed":
        pending_gates = [k for k, v in (gates or {}).items() if v == "pending"]
        if pending_gates:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"workflow is done but gates are still pending: {', '.join(sorted(pending_gates))}",
                )
            )

    return issues


def reconcile_gates(status: Dict[str, Any]) -> bool:
    """Best-effort reconciliation to avoid obvious 'done but pending gates' inconsistencies."""
    if not isinstance(status.get("gates"), dict):
        return False

    changed = False
    gates: Dict[str, Any] = status["gates"]

    comms_state = status.get("comms", {}).get("state") if isinstance(status.get("comms"), dict) else None
    if comms_state in {"ready", "fallback_only"}:
        if gates.get("COMMS_READY") != "pass":
            gates["COMMS_READY"] = "pass"
            changed = True

    # Requirements ACK implies both review approval + client ACK in this workflow model
    ack_requests = status.get("ack_requests") if isinstance(status.get("ack_requests"), list) else []
    for ack in ack_requests:
        if not isinstance(ack, dict):
            continue
        if ack.get("type") == "requirements_review" and ack.get("status") == "approved":
            for gate in ["REQ_REVIEW_APPROVED", "REQ_CLIENT_ACK"]:
                if gates.get(gate) != "pass":
                    gates[gate] = "pass"
                    changed = True
        if ack.get("type") == "final_client_ack" and ack.get("status") == "approved":
            if gates.get("FINAL_CLIENT_ACK") != "pass":
                gates["FINAL_CLIENT_ACK"] = "pass"
                changed = True

    # If workflow is explicitly marked done, mark remaining gates as pass to avoid deadlocks.
    if status.get("current_phase") == "done" and status.get("phase_status") == "completed":
        for gate_name in list(gates.keys()):
            if gates.get(gate_name) == "pending":
                gates[gate_name] = "pass"
                changed = True

    return changed


def _next_phase(phase: str) -> str:
    try:
        idx = PHASES.index(phase)
    except ValueError:
        return PHASES[0]
    return PHASES[min(idx + 1, len(PHASES) - 1)]


def compute_next_transition(status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a patch-like dict of fields to update for the next orchestrator transition."""
    phase = status.get("current_phase")
    if not isinstance(phase, str) or phase not in PHASE_ACTORS:
        # Kickoff/reset to the first phase
        owner, _reviewer = PHASE_ACTORS["bootstrap_comms"]
        return {
            "current_phase": "bootstrap_comms",
            "current_actor": owner,
            "phase_status": "in_progress",
            "actor_status": "not_started",
            "review_status": "not_started",
        }

    if phase == "done":
        return None

    owner, reviewer = PHASE_ACTORS[phase]
    current_actor = status.get("current_actor")
    phase_status = status.get("phase_status")
    actor_status = status.get("actor_status")
    review_status = status.get("review_status")

    if phase_status in ("", None, "not_started"):
        return {
            "current_actor": owner,
            "phase_status": "in_progress",
            "actor_status": "not_started",
            "review_status": "not_started",
        }

    if current_actor == owner:
        if actor_status == "completed":
            if reviewer:
                return {
                    "current_actor": reviewer,
                    "phase_status": "awaiting_review",
                    "actor_status": "not_started",
                    "review_status": "in_review",
                }
            # No reviewer: complete phase and advance
            next_phase = _next_phase(phase)
            next_owner, _next_reviewer = PHASE_ACTORS[next_phase]
            return {
                "current_phase": next_phase,
                "current_actor": next_owner,
                "phase_status": "in_progress" if next_phase != "done" else "completed",
                "actor_status": "not_started" if next_phase != "done" else "completed",
                "review_status": "not_started" if next_phase != "done" else "approved",
            }
        # Still waiting on owner
        return None

    if reviewer and current_actor == reviewer:
        if review_status == "approved":
            next_phase = _next_phase(phase)
            next_owner, _next_reviewer = PHASE_ACTORS[next_phase]
            return {
                "current_phase": next_phase,
                "current_actor": next_owner,
                "phase_status": "in_progress" if next_phase != "done" else "completed",
                "actor_status": "not_started" if next_phase != "done" else "completed",
                "review_status": "not_started" if next_phase != "done" else "approved",
            }
        if review_status == "changes_requested":
            return {
                "current_actor": owner,
                "phase_status": "in_progress",
                "actor_status": "not_started",
                "review_status": "not_started",
            }
        # Still waiting on reviewer decision
        return None

    # Unknown actor for this phase: reset to owner
    return {
        "current_actor": owner,
        "phase_status": "in_progress",
        "actor_status": "not_started",
        "review_status": "not_started",
    }


def append_history(history_path: Path, *, from_status: Dict[str, Any], to_status: Dict[str, Any]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)

    if not history_path.exists():
        history_path.write_text(",".join(HISTORY_HEADER) + "\n", encoding="utf-8")

    # Ensure header is correct (best effort)
    first_line = history_path.read_text(encoding="utf-8").splitlines()[:1]
    if not first_line or first_line[0].strip() != ",".join(HISTORY_HEADER):
        # Don’t rewrite history automatically; just append compatible rows.
        pass

    row = [
        _utc_now_iso(),
        str(from_status.get("current_phase", "")),
        str(from_status.get("phase_status", "")),
        str(from_status.get("current_actor", "")),
        str(to_status.get("current_phase", "")),
        str(to_status.get("current_actor", "")),
        str(to_status.get("phase_status", "")),
    ]
    with history_path.open("a", encoding="utf-8") as f:
        f.write(",".join(row) + "\n")


def _format_issues(issues: List[ValidationIssue]) -> str:
    lines = []
    for issue in issues:
        prefix = "ERROR" if issue.level == "error" else "WARN"
        lines.append(f"{prefix}: {issue.message}")
    return "\n".join(lines)


def _cmd_validate(args: argparse.Namespace) -> int:
    status_path = Path(args.status_file)
    try:
        status = _load_json(status_path)
    except Exception as e:
        print(f"ERROR: Failed to load {status_path}: {e}", file=sys.stderr)
        return 1

    issues = validate_status(status)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    if issues:
        print(_format_issues(issues), file=sys.stderr)

    if args.strict and warnings:
        return 1
    return 1 if errors else 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    status_path = Path(args.status_file)
    try:
        status = _load_json(status_path)
    except Exception as e:
        print(f"ERROR: Failed to load {status_path}: {e}", file=sys.stderr)
        return 1

    changed = reconcile_gates(status)
    if not changed:
        print("No reconciliation changes needed.")
        return 0

    if args.apply:
        _atomic_write_json(status_path, status)
        print("Reconciled gates and wrote status.json.")
    else:
        print("Reconciliation changes available (run with --apply to write).")
    return 0


def _cmd_next(args: argparse.Namespace) -> int:
    status_path = Path(args.status_file)
    try:
        status = _load_json(status_path)
    except Exception as e:
        print(f"ERROR: Failed to load {status_path}: {e}", file=sys.stderr)
        return 1

    phase = status.get("current_phase")
    actor = status.get("current_actor")
    if phase == "done":
        print("Workflow is already done.")
        return 0

    if isinstance(phase, str) and phase in PHASE_ACTORS:
        owner, reviewer = PHASE_ACTORS[phase]
        print(f"current_phase={phase} owner={owner} reviewer={reviewer or '-'} current_actor={actor}")
    else:
        print("current_phase is invalid/empty; next transition will kickoff bootstrap_comms.")
    return 0


def _cmd_step(args: argparse.Namespace) -> int:
    status_path = Path(args.status_file)
    history_path = Path(args.history_file)

    try:
        status = _load_json(status_path)
    except Exception as e:
        print(f"ERROR: Failed to load {status_path}: {e}", file=sys.stderr)
        return 1

    if status.get("current_phase") == "done" and status.get("phase_status") == "completed":
        print("Workflow is already done. Use `orchestrator.py restart --apply` to start over.")
        return 0

    if args.reconcile:
        reconcile_gates(status)

    patch = compute_next_transition(status)
    if not patch:
        print("No orchestrator transition available (waiting on current actor/reviewer).")
        return 0

    from_status = dict(status)
    status.update(patch)
    to_status = status

    if args.apply:
        _atomic_write_json(status_path, status)
        append_history(history_path, from_status=from_status, to_status=to_status)
        print(
            f"Transitioned {from_status.get('current_phase')}:{from_status.get('current_actor')} -> "
            f"{to_status.get('current_phase')}:{to_status.get('current_actor')}"
        )
    else:
        print(
            "Dry-run transition:\n"
            f"  from {from_status.get('current_phase')}:{from_status.get('current_actor')} "
            f"({from_status.get('phase_status')})\n"
            f"  to   {to_status.get('current_phase')}:{to_status.get('current_actor')} "
            f"({to_status.get('phase_status')})\n"
            "Run with --apply to write status.json and append history."
        )
    return 0


def _cmd_restart(args: argparse.Namespace) -> int:
    status_path = Path(args.status_file)
    history_path = Path(args.history_file)

    try:
        status = _load_json(status_path)
    except Exception as e:
        print(f"ERROR: Failed to load {status_path}: {e}", file=sys.stderr)
        return 1

    from_status = dict(status)

    cycle = status.get("cycle")
    if isinstance(cycle, int):
        status["cycle"] = cycle + 1
    else:
        status["cycle"] = 1

    owner, _reviewer = PHASE_ACTORS["bootstrap_comms"]
    status["current_phase"] = "bootstrap_comms"
    status["current_actor"] = owner
    status["phase_status"] = "in_progress"
    status["actor_status"] = "not_started"
    status["review_status"] = "not_started"

    if args.clear_qa:
        status["client_questions"] = []
        status["client_answers"] = []
        status["client_action_required"] = False

    if args.clear_acks:
        status["ack_requests"] = []

    # Reset gates to pending on restart
    if isinstance(status.get("gates"), dict):
        for k in list(status["gates"].keys()):
            status["gates"][k] = "pending"

    if isinstance(status.get("timestamps"), dict):
        status["timestamps"]["workflow_started_at"] = _utc_now_iso()
        status["timestamps"]["phase_started_at"] = ""
        status["timestamps"]["phase_ended_at"] = ""

    if args.apply:
        _atomic_write_json(status_path, status)
        append_history(history_path, from_status=from_status, to_status=status)
        print("Workflow restarted at bootstrap_comms.")
    else:
        print("Dry-run restart available (run with --apply to write).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator.py")
    parser.add_argument("--status-file", default="status.json")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate", help="Validate status.json structure")
    p_validate.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p_validate.set_defaults(func=_cmd_validate)

    p_reconcile = sub.add_parser("reconcile", help="Reconcile obvious inconsistencies (best effort)")
    p_reconcile.add_argument("--apply", action="store_true", help="Write changes to status.json")
    p_reconcile.set_defaults(func=_cmd_reconcile)

    p_next = sub.add_parser("next", help="Print current phase/actor mapping")
    p_next.set_defaults(func=_cmd_next)

    p_step = sub.add_parser("step", help="Perform the next orchestrator transition (delegating)")
    p_step.add_argument("--history-file", default="status_history.csv")
    p_step.add_argument("--apply", action="store_true", help="Write status.json + append history")
    p_step.add_argument("--reconcile", action="store_true", help="Reconcile gates before stepping")
    p_step.set_defaults(func=_cmd_step)

    p_restart = sub.add_parser("restart", help="Restart workflow at bootstrap_comms")
    p_restart.add_argument("--history-file", default="status_history.csv")
    p_restart.add_argument("--apply", action="store_true", help="Write status.json + append history")
    p_restart.add_argument("--clear-qa", action="store_true", help="Clear client_questions/client_answers")
    p_restart.add_argument("--clear-acks", action="store_true", help="Clear ack_requests")
    p_restart.set_defaults(func=_cmd_restart)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
