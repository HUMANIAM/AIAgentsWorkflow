#!/usr/bin/env python3
"""Tests for governance gate answer handling in status handler."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import status_handler


def _base_gate_status(question_id: str = "Q-GATE-RELEASE_APPROVAL-20260208000100") -> dict:
    return {
        "current_phase": "release",
        "realization_status": "waiting_approval",
        "pending_human_gate_id": "RELEASE_APPROVAL",
        "pending_human_question_id": question_id,
        "active_idea_id": "smartbookmarker_ai_powered_boo",
        "questions": [
            {
                "id": question_id,
                "from_role": "orchestrator",
                "to_human": True,
                "required": True,
                "status": "delivered",
                "question": "Release approval required.",
                "context": "release gate",
                "created_at": "2026-02-08T00:01:00Z",
                "kind": "governance_gate",
                "gate_id": "RELEASE_APPROVAL",
            }
        ],
        "answers": [],
        "governance_gates": [
            {
                "id": "RELEASE_APPROVAL",
                "status": "pending",
                "owner": "human_engineer",
                "reason": "",
                "updated_at": "2026-02-08T00:00:00Z",
            }
        ],
    }


def test_handle_gate_answer_requires_strict_tokens(monkeypatch, tmp_path):
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps(_base_gate_status(), indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(status_handler, "STATUS_FILE", status_file)

    result = status_handler.handle_gate_answer("Q-GATE-RELEASE_APPROVAL-20260208000100", "maybe")
    assert result["handled"] is True
    assert result["accepted"] is False
    assert "approve" in result["message"].lower()

    latest = json.loads(status_file.read_text(encoding="utf-8"))
    assert latest["governance_gates"][0]["status"] == "pending"
    assert latest["questions"][0]["status"] == "delivered"


def test_handle_gate_approval_resumes_and_marks_done(monkeypatch, tmp_path):
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps(_base_gate_status(), indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(status_handler, "STATUS_FILE", status_file)

    def _fake_resume():
        current = json.loads(status_file.read_text(encoding="utf-8"))
        current["current_phase"] = "done"
        current["realization_status"] = "completed"
        current["pending_human_gate_id"] = ""
        current["pending_human_question_id"] = ""
        status_file.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "message": "run ok"}

    monkeypatch.setattr(status_handler, "_resume_orchestrator_run", _fake_resume)

    import services.idea_handler as idea_handler

    calls = []

    def _fake_force_set(idea_id: str, status_value: str, owner_user_id=None):
        calls.append((idea_id, status_value))
        return True, "ok"

    monkeypatch.setattr(idea_handler, "force_set_idea_status", _fake_force_set)

    result = status_handler.handle_gate_answer("Q-GATE-RELEASE_APPROVAL-20260208000100", "approve")
    assert result["handled"] is True
    assert result["accepted"] is True
    assert result["decision"] == "approved"
    assert "completed" in result["message"].lower()

    latest = json.loads(status_file.read_text(encoding="utf-8"))
    assert latest["governance_gates"][0]["status"] == "approved"
    assert latest["questions"][0]["status"] == "answered"
    assert calls == [("smartbookmarker_ai_powered_boo", "DONE")]
