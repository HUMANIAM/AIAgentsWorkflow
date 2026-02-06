#!/usr/bin/env python3
"""Status.json handler for reading/writing workflow state"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


# Path to status.json (relative to bot directory)
STATUS_FILE = Path(__file__).parent.parent.parent / "status.json"


def read_status() -> Dict[str, Any]:
    """Read and parse status.json"""
    with open(STATUS_FILE, 'r') as f:
        return json.load(f)


def write_status(status: Dict[str, Any]) -> None:
    """Write status.json with proper formatting"""
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)
        f.write('\n')


def get_pending_questions() -> List[Dict[str, Any]]:
    """Get all questions with delivery_status='pending'"""
    status = read_status()
    questions = status.get('client_questions', [])
    return [q for q in questions if q.get('delivery_status') == 'pending']


def get_delivered_questions() -> List[Dict[str, Any]]:
    """Get all questions with delivery_status='delivered' (awaiting answer)"""
    status = read_status()
    questions = status.get('client_questions', [])
    return [q for q in questions if q.get('delivery_status') == 'delivered']


def mark_question_delivered(question_id: str) -> None:
    """Mark a question as delivered to client"""
    status = read_status()
    for q in status.get('client_questions', []):
        if q.get('id') == question_id:
            q['delivery_status'] = 'delivered'
            q['delivered_at'] = datetime.now(timezone.utc).isoformat()
            break
    write_status(status)


def write_answer(question_id: str, answer: str, source: str = "telegram") -> None:
    """Write client answer to status.json"""
    status = read_status()
    
    # Find the question and mark as answered
    for q in status.get('client_questions', []):
        if q.get('id') == question_id:
            q['delivery_status'] = 'answered'
            break
    
    # Add answer
    answer_obj = {
        "question_id": question_id,
        "answer": answer,
        "source": source,
        "answered_at": datetime.now(timezone.utc).isoformat()
    }
    
    if 'client_answers' not in status:
        status['client_answers'] = []
    status['client_answers'].append(answer_obj)
    
    # Check if all questions are answered
    pending = [q for q in status.get('client_questions', []) 
               if q.get('delivery_status') in ('pending', 'delivered')]
    
    if not pending:
        # All questions answered, clear the flag
        status['client_action_required'] = False
    
    write_status(status)


def is_client_action_required() -> bool:
    """Check if client action is required"""
    status = read_status()
    return status.get('client_action_required', False)


def get_current_phase() -> str:
    """Get current workflow phase"""
    status = read_status()
    return status.get('current_phase', '')


def get_current_actor() -> str:
    """Get current actor"""
    status = read_status()
    return status.get('current_actor', '')
