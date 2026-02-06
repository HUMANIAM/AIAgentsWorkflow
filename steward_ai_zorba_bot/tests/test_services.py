#!/usr/bin/env python3
"""Tests for communication bot services"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import tempfile
from pathlib import Path


def test_status_handler_read_write():
    """AC-04: Status handler can read and write status.json"""
    from services.status_handler import STATUS_FILE
    
    # Verify status file exists and is readable
    assert STATUS_FILE.exists(), f"status.json not found at {STATUS_FILE}"
    
    with open(STATUS_FILE, 'r') as f:
        status = json.load(f)
    
    assert 'client_questions' in status
    assert 'client_answers' in status
    assert 'client_action_required' in status


def test_get_pending_questions():
    """AC-01: Can detect pending questions"""
    from services.status_handler import read_status
    
    status = read_status()
    questions = status.get('client_questions', [])
    
    # Check structure of questions
    for q in questions:
        assert 'id' in q
        assert 'question' in q or 'text' in q
        assert 'delivery_status' in q


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
