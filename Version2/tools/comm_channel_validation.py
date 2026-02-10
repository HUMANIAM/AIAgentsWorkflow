#!/usr/bin/env python3
"""Communication-first validation runner with strict timeout."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
SRC_DIR = TOOLS_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from orchestrator import utils as orch_utils


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime] = None) -> str:
    dt = dt or utc_now()
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_artifacts_dir(status_path: Path) -> Path:
    base = status_path.parent / "artifacts"
    try:
        status = read_json(status_path)
    except Exception:
        return base / "simulation_baseline"

    headline = str(status.get("active_idea_headline", "")).strip()
    idea_id = str(status.get("active_idea_id", "")).strip()
    slug = orch_utils.slugify(headline) or orch_utils.slugify(idea_id) or "simulation_baseline"
    return base / slug


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@dataclass
class ScenarioResult:
    name: str
    start: datetime
    deadline: datetime
    end: datetime
    passed: bool
    details: List[str] = field(default_factory=list)


class Timeline:
    def __init__(self) -> None:
        self.events: List[Tuple[datetime, str, str]] = []

    def add(self, scenario: str, message: str) -> None:
        self.events.append((utc_now(), scenario, message))

    def to_markdown(self) -> str:
        lines = ["# Communication Channel Timeline", "", "| Timestamp (UTC) | Scenario | Event |", "|---|---|---|"]
        for ts, scenario, message in self.events:
            safe = message.replace("|", "\\|")
            lines.append(f"| {utc_iso(ts)} | {scenario} | {safe} |")
        return "\n".join(lines) + "\n"


def parse_ideas(ideas_dir: Path) -> List[Dict[str, Any]]:
    if not ideas_dir.exists() or not ideas_dir.is_dir():
        return []

    ideas: List[Dict[str, Any]] = []
    for file_path in sorted(ideas_dir.glob("*.md")):
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue

        idea = {"id": file_path.stem, "status": "", "chat_history": []}
        in_chat = False
        for line in lines:
            if line.startswith("## ID:"):
                idea["id"] = line.replace("## ID:", "").strip() or file_path.stem
            if line.startswith("**Status:**"):
                idea["status"] = line.replace("**Status:**", "").strip()
            elif line.startswith("### Chat History"):
                in_chat = True
            elif line.startswith("### Runtime Adjustments"):
                in_chat = False
            elif in_chat and line.startswith("**User:**"):
                idea["chat_history"].append({"role": "user", "content": line.replace("**User:**", "").strip()})
            elif in_chat and (line.startswith("**GPT:**") or line.startswith("**Gpt:**")):
                cleaned = line.replace("**GPT:**", "").replace("**Gpt:**", "").strip()
                idea["chat_history"].append({"role": "gpt", "content": cleaned})
        ideas.append(idea)
    return ideas


def ensure_single_bot_process() -> Tuple[bool, str]:
    try:
        import re
        import subprocess

        cp = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            capture_output=True,
            text=True,
            check=False,
        )
        candidates: List[str] = []
        for row in cp.stdout.splitlines():
            row = row.strip()
            if not row:
                continue

            parts = row.split(maxsplit=1)
            if len(parts) != 2:
                continue

            pid, args = parts
            if re.search(r"\bpython(?:3(?:\.\d+)?)?\b.*\bmain\.py\b", args):
                # Avoid counting this validator process if invoked as python ...main.py elsewhere.
                if "comm_channel_validation.py" in args:
                    continue
                candidates.append(f"{pid} {args}")

        if len(candidates) == 1:
            return True, f"single bot process confirmed ({candidates[0]})"
        if len(candidates) == 0:
            return False, "no running bot process detected"
        return False, f"multiple bot processes detected ({len(candidates)})"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"failed to inspect bot process: {exc}"


def inject_pending_question(status_path: Path, question_id: str) -> None:
    status = read_json(status_path)
    status.setdefault("questions", [])
    status.setdefault("answers", [])
    status["questions"] = [q for q in status["questions"] if q.get("id") != question_id]
    status["answers"] = [a for a in status["answers"] if a.get("question_id") != question_id]
    status["questions"].append(
        {
            "id": question_id,
            "from_role": "integration_tester",
            "to_human": True,
            "required": True,
            "status": "pending_delivery",
            "question": "Please confirm communication loop by replying with any text.",
            "context": "Version2 closed-loop validation",
            "created_at": utc_iso(),
        }
    )
    write_json(status_path, status)


def reset_stale_comm_questions(status_path: Path, question_prefix: str = "Q-COMM-") -> int:
    """Remove stale pending/delivered validation questions from previous runs."""
    status = read_json(status_path)
    status.setdefault("questions", [])
    status.setdefault("answers", [])
    stale_ids = {
        q.get("id")
        for q in status["questions"]
        if isinstance(q, dict)
        and isinstance(q.get("id"), str)
        and q.get("id", "").startswith(question_prefix)
        and q.get("status") in {"pending_delivery", "delivered"}
    }
    if not stale_ids:
        return 0

    status["questions"] = [
        q
        for q in status["questions"]
        if not (isinstance(q, dict) and q.get("id") in stale_ids)
    ]
    status["answers"] = [
        a
        for a in status["answers"]
        if not (isinstance(a, dict) and a.get("question_id") in stale_ids)
    ]
    write_json(status_path, status)
    return len(stale_ids)


def scenario_team_question(
    status_path: Path,
    timeout_seconds: int,
    timeline: Timeline,
    question_id: str,
) -> ScenarioResult:
    name = "Scenario 2 - team question closed loop"
    start = utc_now()
    deadline = start + timedelta(seconds=timeout_seconds)
    details: List[str] = []

    inject_pending_question(status_path, question_id)
    timeline.add(name, f"Injected pending question `{question_id}` into status.json")

    delivered_seen = False
    answered_seen = False
    unblock_seen = False

    while utc_now() <= deadline:
        status = read_json(status_path)
        questions = status.get("questions", [])
        answers = status.get("answers", [])

        q = next((item for item in questions if item.get("id") == question_id), None)
        a = next((item for item in answers if item.get("question_id") == question_id), None)

        if isinstance(q, dict):
            q_state = q.get("status")
        else:
            q_state = None

        if not delivered_seen and q_state == "delivered":
            delivered_seen = True
            timeline.add(name, f"Question `{question_id}` marked delivered")
            details.append("question status moved to delivered")

        if not answered_seen and q_state in {"answered", "closed"} and a:
            answered_seen = True
            timeline.add(name, f"Question `{question_id}` marked answered with mapped client answer")
            details.append("answer persisted with matching question_id")

        unresolved = any(
            isinstance(item, dict)
            and item.get("id") == question_id
            and item.get("status") in {"pending_delivery", "delivered"}
            for item in questions
        )
        unblocked = not unresolved

        if not unblock_seen and unblocked:
            unblock_seen = True
            timeline.add(name, "Unblock condition satisfied (no unresolved pending/delivered question state)")
            details.append("unblock condition satisfied")

        if delivered_seen and answered_seen and unblock_seen:
            end = utc_now()
            details.append(f"completed in {(end - start).total_seconds():.1f}s")
            return ScenarioResult(name, start, deadline, end, True, details)

        time.sleep(2)

    end = utc_now()
    if not delivered_seen:
        details.append("FAILED: delivery not observed before timeout")
    if delivered_seen and not answered_seen:
        details.append("FAILED: answer persistence not observed before timeout")
    if answered_seen and not unblock_seen:
        details.append("FAILED: unblock not observed before timeout")
    timeline.add(name, "Timeout reached before full closed loop")
    return ScenarioResult(name, start, deadline, end, False, details)


def scenario_idea_loop(
    ideas_dir: Path,
    timeout_seconds: int,
    timeline: Timeline,
) -> ScenarioResult:
    name = "Scenario 1 - /idea command loop"
    start = utc_now()
    deadline = start + timedelta(seconds=timeout_seconds)
    details: List[str] = []

    baseline = parse_ideas(ideas_dir)
    baseline_ids = {idea["id"] for idea in baseline}
    baseline_count = len(baseline)

    timeline.add(
        name,
        "Waiting for manual Telegram actions: /idea -> one message round-trip -> /idea stop",
    )

    observed_new_idea = None

    while utc_now() <= deadline:
        current = parse_ideas(ideas_dir)
        if len(current) > baseline_count:
            new_items = [idea for idea in current if idea["id"] not in baseline_ids]
            for idea in new_items:
                chat = idea.get("chat_history", [])
                has_user = any(msg.get("role") == "user" for msg in chat)
                has_gpt = any(msg.get("role") == "gpt" for msg in chat)
                if has_user and has_gpt and idea.get("status", "").upper() in {
                    "NEW",
                    "REFINING",
                    "REFINED",
                    "PLANNED",
                    "ACTIVATED",
                    "EXECUTING",
                    "WAITING_REALIZATION_APPROVAL",
                    "DONE",
                }:
                    observed_new_idea = idea
                    break

            if observed_new_idea:
                if observed_new_idea.get("status", "").upper() == "REFINED":
                    timeline.add(name, f"New idea `{observed_new_idea['id']}` observed with status REFINED")
                    details.append("/idea stop outcome observed (status REFINED)")
                else:
                    timeline.add(name, f"New idea `{observed_new_idea['id']}` observed with status {observed_new_idea.get('status')}")
                    details.append("new idea artifact observed")
                details.append("chat round-trip detected in per-idea files")
                end = utc_now()
                details.append(f"completed in {(end - start).total_seconds():.1f}s")
                return ScenarioResult(name, start, deadline, end, True, details)

        time.sleep(2)

    end = utc_now()
    details.append("FAILED: /idea closed loop evidence not observed before timeout")
    timeline.add(name, "Timeout reached before /idea artifact loop completion")
    return ScenarioResult(name, start, deadline, end, False, details)


def write_assertions(path: Path, results: List[ScenarioResult]) -> None:
    lines = ["# Communication Channel Assertions", ""]
    for result in results:
        lines.append(f"## {result.name}")
        lines.append(f"- Start: `{utc_iso(result.start)}`")
        lines.append(f"- Deadline: `{utc_iso(result.deadline)}`")
        lines.append(f"- End: `{utc_iso(result.end)}`")
        lines.append(f"- Status: {'PASS' if result.passed else 'FAIL'}")
        for detail in result.details:
            lines.append(f"- {detail}")
        lines.append("")

    overall = all(result.passed for result in results)
    lines.append("## Overall")
    lines.append(f"- Verdict: {'PASS' if overall else 'FAIL'}")
    if not overall:
        lines.append("- Required action: backend fix + integration retest loop")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_remediation(remediation_path: Path, results: List[ScenarioResult]) -> None:
    failed = [r for r in results if not r.passed]
    if not failed:
        return

    lines = []
    lines.append("\n## Communication Validation Failures")
    for res in failed:
        lines.append(f"- {res.name}: {'; '.join(res.details)}")
    lines.append("- Action owner: backend + integration tester")
    lines.append("- Retry policy: up to 3 fix-retry cycles")

    with remediation_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run communication-first validation with strict timeout")
    parser.add_argument("--status-file", default="Version2/agent_runtime/status.json")
    parser.add_argument("--ideas-dir", default="Version2/agent_runtime/ideas")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--run", choices=["all", "question", "idea"], default="all")
    parser.add_argument("--timeline-out", default="")
    parser.add_argument("--assertions-out", default="")
    parser.add_argument("--remediation-out", default="")
    args = parser.parse_args()

    status_path = Path(args.status_file)
    ideas_dir = Path(args.ideas_dir)
    artifacts_dir = resolve_artifacts_dir(status_path)
    timeline_out = Path(args.timeline_out) if args.timeline_out else artifacts_dir / "08_comm_channel_timeline.md"
    assertions_out = Path(args.assertions_out) if args.assertions_out else artifacts_dir / "09_comm_channel_assertions.md"
    remediation_out = Path(args.remediation_out) if args.remediation_out else artifacts_dir / "06_failures_and_remediation.md"

    timeline_out.parent.mkdir(parents=True, exist_ok=True)
    assertions_out.parent.mkdir(parents=True, exist_ok=True)
    remediation_out.parent.mkdir(parents=True, exist_ok=True)

    timeline = Timeline()

    ok_single, msg = ensure_single_bot_process()
    timeline.add("Preflight", msg)
    if not ok_single:
        timeline_out.write_text(timeline.to_markdown(), encoding="utf-8")
        write_assertions(assertions_out, [
            ScenarioResult(
                name="Preflight",
                start=utc_now(),
                deadline=utc_now(),
                end=utc_now(),
                passed=False,
                details=[msg],
            )
        ])
        return 2

    results: List[ScenarioResult] = []

    if args.run in {"all", "question"}:
        dropped = reset_stale_comm_questions(status_path)
        if dropped:
            timeline.add("Preflight", f"Cleared stale validation questions: {dropped}")
        qid = f"Q-COMM-{utc_now().strftime('%Y%m%d%H%M%S')}"
        timeline.add("Preflight", f"Prepared question scenario id `{qid}`")
        results.append(scenario_team_question(status_path, args.timeout_seconds, timeline, qid))

    if args.run in {"all", "idea"}:
        results.append(scenario_idea_loop(ideas_dir, args.timeout_seconds, timeline))

    timeline_out.write_text(timeline.to_markdown(), encoding="utf-8")
    write_assertions(assertions_out, results)
    append_remediation(remediation_out, results)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
