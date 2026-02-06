#!/usr/bin/env python3
"""Idea handler - manages idea brainstorming sessions with GPT"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import shutil

# Paths - use agent_runtime/ as base
PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENT_RUNTIME = PROJECT_ROOT / "agent_runtime"
IDEAS_FILE = AGENT_RUNTIME / "ideas.md"
PLUGIN_DIR = AGENT_RUNTIME / "plugin"
STATUS_FILE = AGENT_RUNTIME / "status.json"

# Idea states
STATE_NEW = "NEW"
STATE_PLANNED = "PLANNED"
STATE_ACTIVATED = "ACTIVATED"
STATE_DONE = "DONE"
VALID_STATES = [STATE_NEW, STATE_PLANNED, STATE_ACTIVATED, STATE_DONE]

# Active sessions per user (in-memory, survives during bot runtime)
_active_sessions: Dict[int, str] = {}  # user_id -> idea_id


def _generate_idea_id(headline: str) -> str:
    """Generate a slug ID from headline"""
    slug = re.sub(r'[^a-z0-9]+', '_', headline.lower()).strip('_')
    return slug[:30] if len(slug) > 30 else slug


def _read_ideas_file() -> str:
    """Read ideas.md content"""
    if IDEAS_FILE.exists():
        return IDEAS_FILE.read_text()
    return "# Ideas Log\n\n"


def _write_ideas_file(content: str):
    """Write ideas.md content"""
    IDEAS_FILE.write_text(content)


def _parse_ideas() -> List[Dict]:
    """Parse ideas.md into list of idea dicts"""
    content = _read_ideas_file()
    ideas = []
    
    # Split by idea sections
    sections = re.split(r'\n---\n## ID: ', content)
    
    for section in sections[1:]:  # Skip header
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        idea_id = lines[0].strip()
        idea = {'id': idea_id, 'headline': '', 'status': 'NEW', 'chat_history': []}
        
        in_chat = False
        for line in lines[1:]:
            if line.startswith('**Headline:**'):
                idea['headline'] = line.replace('**Headline:**', '').strip()
            elif line.startswith('**Status:**'):
                idea['status'] = line.replace('**Status:**', '').strip()
            elif line.startswith('### Chat History'):
                in_chat = True
            elif in_chat and line.startswith('**User:**'):
                idea['chat_history'].append({'role': 'user', 'content': line.replace('**User:**', '').strip()})
            elif in_chat and line.startswith('**GPT:**'):
                idea['chat_history'].append({'role': 'gpt', 'content': line.replace('**GPT:**', '').strip()})
        
        ideas.append(idea)
    
    return ideas


def create_idea(user_id: int) -> str:
    """Start a new idea session, return idea_id"""
    # Generate temporary ID (will be replaced when we get headline)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    idea_id = f"idea_{timestamp}"
    
    # Store active session
    _active_sessions[user_id] = idea_id
    
    # Ensure ideas file exists
    if not IDEAS_FILE.exists():
        IDEAS_FILE.parent.mkdir(parents=True, exist_ok=True)
        IDEAS_FILE.write_text("# Ideas Log\n\n")
    
    # Create initial entry in ideas.md
    content = _read_ideas_file()
    new_entry = f"""
---
## ID: {idea_id}
**Headline:** (pending)
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Status:** IN_PROGRESS

### Chat History
"""
    content += new_entry
    _write_ideas_file(content)
    
    return idea_id


def get_active_idea(user_id: int) -> Optional[str]:
    """Get active idea session for user"""
    return _active_sessions.get(user_id)


def add_message(idea_id: str, role: str, text: str):
    """Add a message to idea chat history"""
    content = _read_ideas_file()
    
    # Find the idea section and append message
    marker = f"## ID: {idea_id}"
    if marker in content:
        # Find end of chat history section (before next --- or end of file)
        parts = content.split(marker)
        before = parts[0]
        after = parts[1] if len(parts) > 1 else ""
        
        # Find where to insert (before next --- or at end)
        next_idea = after.find('\n---\n## ID:')
        if next_idea == -1:
            # Last idea, append at end
            after = after.rstrip() + f"\n**{role.capitalize()}:** {text}\n"
        else:
            # Insert before next idea
            idea_section = after[:next_idea]
            rest = after[next_idea:]
            idea_section = idea_section.rstrip() + f"\n**{role.capitalize()}:** {text}\n"
            after = idea_section + rest
        
        content = before + marker + after
        _write_ideas_file(content)


def get_chat_history(idea_id: str) -> List[Dict[str, str]]:
    """Get full chat history for an idea"""
    ideas = _parse_ideas()
    for idea in ideas:
        if idea['id'] == idea_id:
            return idea['chat_history']
    return []


def update_headline(idea_id: str, headline: str):
    """Update the headline for an idea"""
    content = _read_ideas_file()
    
    # Replace (pending) headline
    old_pattern = f"## ID: {idea_id}\n**Headline:** (pending)"
    new_text = f"## ID: {idea_id}\n**Headline:** {headline}"
    content = content.replace(old_pattern, new_text)
    
    # Also update the ID to match headline
    new_id = _generate_idea_id(headline)
    content = content.replace(f"## ID: {idea_id}", f"## ID: {new_id}")
    
    _write_ideas_file(content)
    
    # Update active session
    for user_id, active_id in list(_active_sessions.items()):
        if active_id == idea_id:
            _active_sessions[user_id] = new_id
    
    return new_id


def end_idea(user_id: int) -> Optional[str]:
    """End idea session for user, return idea_id"""
    idea_id = _active_sessions.pop(user_id, None)
    
    if idea_id:
        # Update status to NEW (no longer IN_PROGRESS)
        content = _read_ideas_file()
        content = content.replace(
            f"## ID: {idea_id}\n**Headline:**",
            f"## ID: {idea_id}\n**Headline:**"
        )
        # Mark as NEW instead of IN_PROGRESS
        old = f"**Status:** IN_PROGRESS"
        # Find the right section
        marker = f"## ID: {idea_id}"
        if marker in content:
            parts = content.split(marker)
            if len(parts) > 1:
                section = parts[1]
                next_idea = section.find('\n---\n## ID:')
                if next_idea == -1:
                    idea_section = section
                    rest = ""
                else:
                    idea_section = section[:next_idea]
                    rest = section[next_idea:]
                
                idea_section = idea_section.replace("**Status:** IN_PROGRESS", "**Status:** NEW")
                content = parts[0] + marker + idea_section + rest
                _write_ideas_file(content)
    
    return idea_id


def list_ideas() -> List[Dict]:
    """List all ideas with id, headline, status"""
    return _parse_ideas()


def list_ideas_by_state(state: str) -> List[Dict]:
    """List ideas filtered by state (case-insensitive)"""
    state_upper = state.upper()
    if state_upper not in VALID_STATES:
        return []
    return [idea for idea in _parse_ideas() if idea['status'].upper() == state_upper]


def _update_idea_status(idea_id: str, new_status: str) -> bool:
    """Update the status of an idea in ideas.md"""
    content = _read_ideas_file()
    marker = f"## ID: {idea_id}"
    
    if marker not in content:
        return False
    
    parts = content.split(marker)
    if len(parts) < 2:
        return False
    
    section = parts[1]
    next_idea = section.find('\n---\n## ID:')
    if next_idea == -1:
        idea_section = section
        rest = ""
    else:
        idea_section = section[:next_idea]
        rest = section[next_idea:]
    
    # Replace any status with new status
    for old_state in VALID_STATES + ["IN_PROGRESS"]:
        idea_section = idea_section.replace(f"**Status:** {old_state}", f"**Status:** {new_status}")
    
    content = parts[0] + marker + idea_section + rest
    _write_ideas_file(content)
    return True


def generate_context_file(idea_id: str, context_content: str) -> str:
    """Create plugin/context_{idea_id}.md file"""
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    context_file.write_text(context_content)
    return str(context_file)


def plan_idea(idea_id: str, context_content: str) -> Tuple[bool, str]:
    """
    Plan an idea: generate context file and set status to PLANNED.
    Returns (success, message)
    """
    # Find the idea
    ideas = _parse_ideas()
    idea = None
    for i in ideas:
        if i['id'] == idea_id:
            idea = i
            break
    
    if not idea:
        return False, f"Idea not found: {idea_id}"
    
    if idea['status'].upper() not in [STATE_NEW, "IN_PROGRESS"]:
        return False, f"Idea must be NEW to plan. Current status: {idea['status']}"
    
    # Generate context file
    context_path = generate_context_file(idea_id, context_content)
    
    # Update status to PLANNED
    _update_idea_status(idea_id, STATE_PLANNED)
    
    return True, f"Planned idea: {idea['headline']}\nContext file: {context_path}"


def activate_idea(idea_id: str) -> Tuple[bool, str]:
    """
    Activate an idea: backup context.md, copy idea context, reset status.json.
    Returns (success, message)
    """
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    main_context = PLUGIN_DIR / "context.md"
    
    # Find the idea
    ideas = _parse_ideas()
    idea = None
    for i in ideas:
        if i['id'] == idea_id:
            idea = i
            break
    
    if not idea:
        return False, f"Idea not found: {idea_id}"
    
    if idea['status'].upper() != STATE_PLANNED:
        return False, f"Idea must be PLANNED to activate. Current status: {idea['status']}. Run `/idea plan {idea_id}` first."
    
    if not context_file.exists():
        return False, f"Context file not found. Run `/idea plan {idea_id}` first."
    
    # Backup current context.md if it exists
    if main_context.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = PLUGIN_DIR / f"context_backup_{timestamp}.md"
        shutil.copy(main_context, backup_path)
    
    # Copy idea context to main context
    content = context_file.read_text()
    main_context.write_text(content)
    
    headline = idea['headline']
    
    # Reset status.json to default workflow state
    _reset_status_json(headline)
    
    # Update idea status to ACTIVATED
    _update_idea_status(idea_id, STATE_ACTIVATED)
    
    return True, f"Activated idea: {headline}"


def complete_idea(idea_id: str) -> Tuple[bool, str]:
    """
    Mark an idea as DONE.
    Returns (success, message)
    """
    # Find the idea
    ideas = _parse_ideas()
    idea = None
    for i in ideas:
        if i['id'] == idea_id:
            idea = i
            break
    
    if not idea:
        return False, f"Idea not found: {idea_id}"
    
    if idea['status'].upper() != STATE_ACTIVATED:
        return False, f"Idea must be ACTIVATED to mark as done. Current status: {idea['status']}"
    
    # Update status to DONE
    _update_idea_status(idea_id, STATE_DONE)
    
    return True, f"Completed idea: {idea['headline']}"


def _reset_status_json(headline: str):
    """Reset status.json to default workflow state with new idea headline"""
    default_status = {
        "problem": {
            "source": "plugin/context.md",
            "text": headline
        },
        "cycle": 0,
        "current_phase": "not_started",
        "current_actor": "orchestrator",
        "phase_status": "pending",
        "actor_status": "pending",
        "review_status": "pending",
        "comms": {
            "primary": "telegram",
            "fallback": "status_file",
            "state": "ready",
            "last_checked_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        "client_action_required": False,
        "client_channel": {
            "type": "telegram",
            "allowed_user_ids": [6660576747]
        },
        "client_questions": [],
        "client_answers": [],
        "ack_requests": [],
        "changesets": {
            "active": None,
            "queue": [],
            "policy": {
                "commit_cap": 50,
                "client_ack_required_for_merge": True,
                "only_orchestrator_merges_to_main": True
            }
        },
        "artifacts": {},
        "gates": {
            "COMMS_READY": "pending",
            "REQ_REVIEW_APPROVED": "pending",
            "REQ_CLIENT_ACK": "pending",
            "ARCH_REVIEW_APPROVED": "pending",
            "DEVOPS_REVIEW_APPROVED": "pending",
            "SECURITY_APPROVED": "pending",
            "FINAL_CLIENT_ACK": "pending"
        },
        "timestamps": {
            "workflow_started_at": "",
            "phase_started_at": "",
            "phase_ended_at": ""
        }
    }
    
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(default_status, indent=2))


# Keep old function name for backwards compatibility
def execute_idea(idea_id: str) -> Tuple[bool, str]:
    """Deprecated: Use activate_idea instead"""
    return activate_idea(idea_id)
