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
    generate_context_file,
    execute_idea
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
            text: Full message text (e.g., "/idea", "/idea stop", "/idea list")
        
        Returns:
            True if command was handled, False otherwise
        """
        text = text.strip()
        
        # /idea stop - end session
        if text == '/idea stop':
            await self.stop_session(user_id)
            return True
        
        # /idea list - list all ideas
        if text == '/idea list':
            await self.list_all(user_id)
            return True
        
        # /idea execute <id> - activate idea
        if text.startswith('/idea execute '):
            idea_id = text.replace('/idea execute ', '').strip()
            await self.execute(user_id, idea_id)
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
        """Stop the current idea session and generate context file"""
        idea_id = get_active_idea(user_id)
        if not idea_id:
            await self.send_func(user_id,
                "❌ No active idea session.\n\n"
                "Send `/idea` to start one.")
            return
        
        await self.send_func(user_id, "⏳ Generating context from our conversation...")
        
        # Get chat history
        history = get_chat_history(idea_id)
        
        if not history:
            end_idea(user_id)
            await self.send_func(user_id,
                "❌ No conversation recorded. Session ended without saving.")
            return
        
        # Generate headline
        headline, description = generate_idea_headline(history)
        new_id = update_headline(idea_id, headline)
        
        # Generate context file
        context_content = generate_context_from_chat(history)
        context_path = generate_context_file(new_id, context_content)
        
        # End session
        end_idea(user_id)
        
        await self.send_func(user_id,
            f"✅ *Idea session ended!*\n\n"
            f"💡 *Headline:* {headline}\n"
            f"📄 *Context file:* `{context_path}`\n\n"
            f"To activate this idea for the team, send:\n"
            f"`/idea execute {new_id}`")
        
        logger.info(f"Ended idea session {new_id} for user {user_id}")
    
    async def list_all(self, user_id: int):
        """List all ideas"""
        ideas = list_ideas()
        
        if not ideas:
            await self.send_func(user_id,
                "📋 *Your Ideas:*\n\n"
                "_No ideas yet. Send `/idea` to start brainstorming!_")
            return
        
        msg = "📋 *Your Ideas:*\n\n"
        for i, idea in enumerate(ideas, 1):
            status_emoji = "🔄" if idea['status'] == 'IN_PROGRESS' else "✅" if idea['status'] == 'EXECUTED' else "💡"
            msg += f"{i}. {status_emoji} `{idea['id']}`\n   {idea['headline']}\n\n"
        
        msg += "_Send `/idea execute <id>` to activate an idea for the team._"
        
        await self.send_func(user_id, msg)
    
    async def execute(self, user_id: int, idea_id: str):
        """Execute an idea - copy to main context and update status.json"""
        # If no ID provided, show available ideas
        if not idea_id:
            await self.list_all(user_id)
            return
        
        success, message = execute_idea(idea_id)
        
        if success:
            await self.send_func(user_id,
                f"✅ *{message}*\n\n"
                f"- Copied to `plugin/context.md`\n"
                f"- Updated `status.json` problem text\n\n"
                f"Run `/orchestrator` to start the team on this!")
        else:
            # Show available ideas on error
            ideas = list_ideas()
            if ideas:
                available = "\n".join([f"  • `{i['id']}`" for i in ideas])
                await self.send_func(user_id, 
                    f"❌ Idea not found: `{idea_id}`\n\n"
                    f"Available ideas:\n{available}\n\n"
                    f"_Use `/idea execute <id>` with one of the above IDs._")
            else:
                await self.send_func(user_id, f"❌ {message}")
