#!/usr/bin/env python3
"""Idea handler - manages idea brainstorming sessions with GPT"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
IDEAS_FILE = PROJECT_ROOT / "ideas.md"
PLUGIN_DIR = PROJECT_ROOT / "plugin"
STATUS_FILE = PROJECT_ROOT / "status.json"

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
    # Generate temporary ID (will be replaced when we get headline from GPT)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    idea_id = f"idea_{timestamp}"
    
    # Store active session
    _active_sessions[user_id] = idea_id
    
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


def generate_context_file(idea_id: str, context_content: str) -> str:
    """Create plugin/context_{idea_id}.md file"""
    PLUGIN_DIR.mkdir(exist_ok=True)
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    context_file.write_text(context_content)
    return str(context_file)


def execute_idea(idea_id: str) -> Tuple[bool, str]:
    """
    Execute an idea: copy context_{idea_id}.md to context.md and update status.json
    Returns (success, message)
    """
    context_file = PLUGIN_DIR / f"context_{idea_id}.md"
    main_context = PLUGIN_DIR / "context.md"
    
    if not context_file.exists():
        return False, f"Context file not found: {context_file}"
    
    # Copy to main context
    content = context_file.read_text()
    main_context.write_text(content)
    
    # Get headline from ideas
    ideas = _parse_ideas()
    headline = idea_id
    for idea in ideas:
        if idea['id'] == idea_id:
            headline = idea['headline']
            break
    
    # Update status.json
    if STATUS_FILE.exists():
        status = json.loads(STATUS_FILE.read_text())
        status['problem']['text'] = headline
        status['problem']['source'] = f"plugin/context_{idea_id}.md"
        STATUS_FILE.write_text(json.dumps(status, indent=2))
    
    # Mark idea as EXECUTED
    content = _read_ideas_file()
    content = content.replace(
        f"## ID: {idea_id}\n**Headline:** {headline}\n**Created:",
        f"## ID: {idea_id}\n**Headline:** {headline}\n**Context File:** plugin/context_{idea_id}.md\n**Created:"
    )
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
            
            idea_section = idea_section.replace("**Status:** NEW", "**Status:** EXECUTED")
            content = parts[0] + marker + idea_section + rest
            _write_ideas_file(content)
    
    return True, f"Activated idea: {headline}"
