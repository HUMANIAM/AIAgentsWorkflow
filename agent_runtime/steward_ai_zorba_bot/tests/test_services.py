#!/usr/bin/env python3
"""Tests for communication bot services"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json


def test_status_handler_read_write():
    """AC-04: Status handler can read and write status.json"""
    from services import status_handler as sh

    original = sh.STATUS_FILE
    try:
        tmp_file = original.parent / "status.test_services.tmp.json"
        tmp_file.write_text(
            json.dumps(
                {
                    "questions": [],
                    "answers": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        sh.STATUS_FILE = tmp_file

        status = sh.read_status()
        assert "questions" in status
        assert "answers" in status

        status["questions"].append(
            {
                "id": "Q-TMP-001",
                "from_role": "qa_engineer",
                "to_human": True,
                "required": True,
                "status": "pending_delivery",
                "question": "tmp?",
                "created_at": "2026-02-08T00:00:00Z",
            }
        )
        sh.write_status(status)
        reread = sh.read_status()
        assert reread["questions"][0]["id"] == "Q-TMP-001"
    finally:
        sh.STATUS_FILE = original
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass


def test_get_pending_questions():
    """AC-01: Can detect pending questions"""
    from services import status_handler as sh

    original = sh.STATUS_FILE
    try:
        tmp_file = original.parent / "status.test_pending.tmp.json"
        tmp_file.write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "id": "Q-PENDING-1",
                            "from_role": "system_analyst",
                            "to_human": True,
                            "required": True,
                            "status": "pending_delivery",
                            "question": "pending?",
                            "created_at": "2026-02-08T00:00:00Z",
                        }
                    ],
                    "answers": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        sh.STATUS_FILE = tmp_file

        pending = sh.get_pending_questions()
        assert len(pending) == 1
        assert pending[0]["id"] == "Q-PENDING-1"
        assert pending[0]["question"] == "pending?"
    finally:
        sh.STATUS_FILE = original
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass


def test_openai_client_structure():
    """AC-02: OpenAI client module has correct structure"""
    from services import openai_client
    
    # Verify module has required functions
    assert hasattr(openai_client, 'get_suggestions')
    assert hasattr(openai_client, 'get_client')
    assert callable(openai_client.get_suggestions)


def test_question_poller_import():
    """AC-03: Question poller can be imported"""
    # Import the module to verify structure
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from apps.telegram.question_poller import QuestionPoller
    
    # Verify class exists and has required methods
    assert hasattr(QuestionPoller, 'format_question_message')
    assert hasattr(QuestionPoller, 'poll_once')
    assert hasattr(QuestionPoller, 'process_answer')
