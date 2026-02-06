#!/usr/bin/env python3
"""Idea chat handler - manages /idea command interactions"""

import logging
from typing import Optional, Callable, Awaitable

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.idea_handler import (
    create_idea,
    get_active_idea,
    add_message,
    get_chat_history,
    update_headline,
    end_idea,
    list_ideas,
    list_ideas_by_state,
    plan_idea,
    activate_idea,
    complete_idea,
    VALID_STATES
)
from services.openai_client import (
    chat_about_idea,
    generate_idea_headline,
    generate_context_from_chat
)

logger = logging.getLogger(__name__)


class IdeaChat:
    """Manages idea brainstorming sessions"""
    
    def __init__(self, send_func: Callable[[int, str], Awaitable[None]]):
        """
        Initialize idea chat handler.
        
        Args:
            send_func: Async function to send messages (user_id, text) -> None
        """
        self.send_func = send_func
    
    async def handle_command(self, user_id: int, text: str) -> bool:
        """
        Handle /idea commands.
        
        Args:
            user_id: Telegram user ID
            text: Full message text (e.g., "/idea", "/idea stop", "/idea list new")
        
        Returns:
            True if command was handled, False otherwise
        """
        text = text.strip()
        
        # /idea stop - end session → NEW
        if text == '/idea stop':
            await self.stop_session(user_id)
            return True
        
        # /idea list {state} - list ideas by state (case-insensitive)
        if text.startswith('/idea list'):
            parts = text.split()
            state = parts[2] if len(parts) > 2 else None
            await self.list_by_state(user_id, state)
            return True
        
        # /idea plan {id} - generate context file → PLANNED
        if text.startswith('/idea plan '):
            idea_id = text.replace('/idea plan ', '').strip()
            await self.plan(user_id, idea_id)
            return True
        
        # /idea activate {id} - activate idea → ACTIVATED
        if text.startswith('/idea activate '):
            idea_id = text.replace('/idea activate ', '').strip()
            await self.activate(user_id, idea_id)
            return True
        
        # /idea done {id} - mark complete → DONE
        if text.startswith('/idea done '):
            idea_id = text.replace('/idea done ', '').strip()
            await self.done(user_id, idea_id)
            return True
        
        # /idea - start new session (no content)
        if text == '/idea':
            await self.start_session(user_id)
            return True
        
        # /idea <content> - start session with initial idea
        if text.startswith('/idea '):
            idea_content = text.replace('/idea ', '').strip()
            await self.start_session_with_idea(user_id, idea_content)
            return True
        
        return False
    
    async def start_session(self, user_id: int):
        """Start a new idea brainstorming session"""
        # Check if already in session
        active = get_active_idea(user_id)
        if active:
            await self.send_func(user_id, 
                f"💡 You already have an active idea session.\n\n"
                f"Continue chatting or send `/idea stop` to end it.")
            return
        
        # Create new idea
        idea_id = create_idea(user_id)
        logger.info(f"Started idea session {idea_id} for user {user_id}")
        
        await self.send_func(user_id,
            "💡 *New idea session started!*\n\n"
            "What do you have in mind? Tell me your idea.\n\n"
            "_Send `/idea stop` when you're done to save it._")
    
    async def start_session_with_idea(self, user_id: int, idea_content: str):
        """Start a new idea session with initial idea content"""
        # Check if already in session
        active = get_active_idea(user_id)
        if active:
            # Continue existing session with this message
            await self.process_message(user_id, idea_content)
            return
        
        # Create new idea
        idea_id = create_idea(user_id)
        logger.info(f"Started idea session {idea_id} for user {user_id} with content")
        
        # Process the initial idea as first message
        await self.process_message(user_id, idea_content)
    
    async def process_message(self, user_id: int, text: str) -> bool:
        """
        Process a message during an active idea session.
        
        Returns:
            True if message was processed (user has active session), False otherwise
        """
        idea_id = get_active_idea(user_id)
        if not idea_id:
            return False
        
        # Record user message
        add_message(idea_id, 'user', text)
        
        # Get full history and send to GPT
        history = get_chat_history(idea_id)
        gpt_response = chat_about_idea(history, text)
        
        # Record GPT response
        add_message(idea_id, 'gpt', gpt_response)
        
        # Send to user
        await self.send_func(user_id, f"🤖 {gpt_response}")
        
        logger.info(f"Idea {idea_id}: User said '{text[:50]}...', GPT responded")
        return True
    
    async def stop_session(self, user_id: int):
        """Stop the current idea session → state=NEW (lazy: no GPT call yet)"""
        idea_id = get_active_idea(user_id)
        if not idea_id:
            await self.send_func(user_id,
                "❌ No active idea session.\n\n"
                "Send `/idea` to start one.")
            return
        
        # Get chat history
        history = get_chat_history(idea_id)
        
        if not history:
            end_idea(user_id)
            await self.send_func(user_id,
                "❌ No conversation recorded. Session ended without saving.")
            return
        
        # Generate headline only (lazy - no context file yet)
        await self.send_func(user_id, "⏳ Generating headline...")
        headline, description = generate_idea_headline(history)
        new_id = update_headline(idea_id, headline)
        
        # End session - marks as NEW
        end_idea(user_id)
        
        await self.send_func(user_id,
            f"✅ *Idea saved!*\n\n"
            f"💡 *Headline:* {headline}\n"
            f"📝 *ID:* `{new_id}`\n"
            f"📊 *Status:* NEW\n\n"
            f"*Next steps:*\n"
            f"1. `/idea plan {new_id}` - Generate context file\n"
            f"2. `/idea activate {new_id}` - Activate for team\n\n"
            f"_Use `/idea list new` to see all new ideas._")
        
        logger.info(f"Ended idea session {new_id} for user {user_id} → NEW")
    
    async def list_by_state(self, user_id: int, state: str = None):
        """List ideas filtered by state (case-insensitive)"""
        # Get status emoji mapping
        status_emojis = {
            'NEW': '💡',
            'PLANNED': '📋',
            'ACTIVATED': '🚀',
            'DONE': '✅',
            'IN_PROGRESS': '🔄'
        }
        
        if state:
            state_upper = state.upper()
            if state_upper not in VALID_STATES:
                await self.send_func(user_id,
                    f"❌ Invalid state: `{state}`\n\n"
                    f"Valid states: `new`, `planned`, `activated`, `done`")
                return
            
            ideas = list_ideas_by_state(state_upper)
            title = f"📋 *Ideas ({state_upper}):*"
        else:
            ideas = list_ideas()
            title = "📋 *All Ideas:*"
        
        if not ideas:
            await self.send_func(user_id,
                f"{title}\n\n"
                f"_No ideas found. Send `/idea` to start brainstorming!_")
            return
        
        msg = f"{title}\n\n"
        for i, idea in enumerate(ideas, 1):
            emoji = status_emojis.get(idea['status'].upper(), '❓')
            msg += f"{i}. {emoji} `{idea['id']}`\n   {idea['headline']} ({idea['status']})\n\n"
        
        msg += "*Commands:*\n"
        msg += "• `/idea plan <id>` - Generate context file\n"
        msg += "• `/idea activate <id>` - Activate for team\n"
        msg += "• `/idea done <id>` - Mark complete"
        
        await self.send_func(user_id, msg)
    
    async def plan(self, user_id: int, idea_id: str):
        """Plan an idea - generate context file → PLANNED"""
        if not idea_id:
            await self.send_func(user_id,
                "❌ Please provide an idea ID.\n\n"
                "Usage: `/idea plan <id>`\n"
                "_Use `/idea list new` to see available ideas._")
            return
        
        await self.send_func(user_id, "⏳ Generating context file from chat history...")
        
        # Get chat history for the idea
        history = get_chat_history(idea_id)
        if not history:
            await self.send_func(user_id, f"❌ No chat history found for idea: `{idea_id}`")
            return
        
        # Generate context content using GPT
        context_content = generate_context_from_chat(history)
        
        # Plan the idea
        success, message = plan_idea(idea_id, context_content)
        
        if success:
            await self.send_func(user_id,
                f"✅ *{message}*\n\n"
                f"📊 *Status:* PLANNED\n\n"
                f"*Next step:*\n"
                f"`/idea activate {idea_id}` - Activate for team")
        else:
            await self.send_func(user_id, f"❌ {message}")
        
        logger.info(f"Planned idea {idea_id} for user {user_id}")
    
    async def activate(self, user_id: int, idea_id: str):
        """Activate an idea - backup context.md, copy idea context, reset status.json"""
        if not idea_id:
            await self.send_func(user_id,
                "❌ Please provide an idea ID.\n\n"
                "Usage: `/idea activate <id>`\n"
                "_Use `/idea list planned` to see available ideas._")
            return
        
        success, message = activate_idea(idea_id)
        
        if success:
            await self.send_func(user_id,
                f"🚀 *{message}*\n\n"
                f"• Backed up previous `context.md`\n"
                f"• Copied idea context to `plugin/context.md`\n"
                f"• Reset `status.json` for new workflow\n\n"
                f"📊 *Status:* ACTIVATED\n\n"
                f"Run `/orchestrator` to start the team on this!\n\n"
                f"_When team finishes, use `/idea done {idea_id}` to mark complete._")
        else:
            await self.send_func(user_id, f"❌ {message}")
        
        logger.info(f"Activated idea {idea_id} for user {user_id}")
    
    async def done(self, user_id: int, idea_id: str):
        """Mark an idea as done → DONE"""
        if not idea_id:
            await self.send_func(user_id,
                "❌ Please provide an idea ID.\n\n"
                "Usage: `/idea done <id>`\n"
                "_Use `/idea list activated` to see active ideas._")
            return
        
        success, message = complete_idea(idea_id)
        
        if success:
            await self.send_func(user_id,
                f"🎉 *{message}*\n\n"
                f"📊 *Status:* DONE\n\n"
                f"Great work! The idea has been completed.\n"
                f"_Use `/idea list done` to see all completed ideas._")
        else:
            await self.send_func(user_id, f"❌ {message}")
        
        logger.info(f"Completed idea {idea_id} for user {user_id}")
