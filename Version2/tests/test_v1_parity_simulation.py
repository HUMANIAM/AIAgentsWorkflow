#!/usr/bin/env python3
"""Functional parity simulation for question->answer->unblock loop."""

import json
from pathlib import Path

import sys
repo_root = Path(__file__).resolve().parents[2]
candidate = repo_root / "agent_runtime" / "steward_ai_zorba_bot"
if not candidate.exists():
    candidate = repo_root / "steward_ai_zorba_bot"
sys.path.insert(0, str(candidate))

import services.status_handler as sh


def test_question_answer_unblock_flow(tmp_path):
    status_file = tmp_path / "status.json"
    status = {
        "questions": [
            {
                "id": "Q-PARITY-001",
                "from_role": "integration_tester",
                "to_human": True,
                "required": True,
                "question": "Confirm scope for v1?",
                "status": "pending_delivery",
                "created_at": "2026-02-08T00:00:00Z",
            }
        ],
        "answers": []
    }
    status_file.write_text(json.dumps(status))

    original = sh.STATUS_FILE
    sh.STATUS_FILE = status_file
    try:
        pending = sh.get_pending_questions()
        assert len(pending) == 1
        assert pending[0]["id"] == "Q-PARITY-001"

        sh.mark_question_delivered("Q-PARITY-001")
        delivered = sh.get_delivered_questions()
        assert len(delivered) == 1

        sh.write_answer("Q-PARITY-001", "Approved scope")
        final_status = sh.read_status()

        assert final_status["answers"]
        assert final_status["answers"][0]["question_id"] == "Q-PARITY-001"
    finally:
        sh.STATUS_FILE = original
