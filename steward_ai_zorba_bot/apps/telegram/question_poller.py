#!/usr/bin/env python3
"""Question poller - polls status.json and delivers questions to client via Telegram"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable

import sys
from pathlib import Path
# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.status_handler import (
    get_pending_questions,
    get_delivered_questions,
    mark_question_delivered,
    write_answer
)
from services.openai_client import get_suggestions

logger = logging.getLogger(__name__)


class QuestionPoller:
    """Polls status.json for pending questions and delivers them with GPT suggestions"""
    
    def __init__(self, send_func: Callable[[int, str], Awaitable[None]], user_ids: list):
        """
        Initialize poller.
        
        Args:
            send_func: Async function to send messages (user_id, text) -> None
            user_ids: List of client user IDs to send questions to
        """
        self.send_func = send_func
        self.user_ids = user_ids
        self.running = False
        self.poll_interval = 10  # seconds (per client decision D-01)
        self.current_question_id: Optional[str] = None
    
    def format_question_message(self, question: dict, suggestions: list) -> str:
        """Format question with suggestions for Telegram"""
        agent = question.get('from_agent', 'the team')
        q_text = question.get('question', question.get('text', ''))
        context = question.get('context', '')
        
        msg = f"📋 *Question from {agent}:*\n\n{q_text}\n"
        
        if context:
            msg += f"\n_Context: {context}_\n"
        
        msg += "\n💡 *Suggested answers:*\n"
        for i, suggestion in enumerate(suggestions, 1):
            msg += f"{i}. {suggestion}\n"
        
        msg += "\n_Reply with 1, 2, 3, or type your own answer._"
        
        return msg
    
    async def deliver_question(self, question: dict) -> bool:
        """
        Deliver a question to client with GPT suggestions.
        
        Returns True if delivered successfully.
        """
        question_id = question.get('id', '')
        q_text = question.get('question', question.get('text', ''))
        context = question.get('context', '')
        
        logger.info(f"Delivering question {question_id}: {q_text[:50]}...")
        
        # Get GPT suggestions
        try:
            suggestions = get_suggestions(q_text, context)
        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")
            suggestions = [
                "Yes, that sounds good",
                "No, let's try something else",
                "I'm not sure, you decide"
            ]
        
        # Format message
        msg = self.format_question_message(question, suggestions)
        
        # Store suggestions for answer matching
        question['_suggestions'] = suggestions
        self.current_question_id = question_id
        
        # Send to all client users
        for user_id in self.user_ids:
            try:
                await self.send_func(user_id, msg)
                logger.info(f"Sent question to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
                return False
        
        # Mark as delivered
        mark_question_delivered(question_id)
        return True
    
    def process_answer(self, text: str) -> Optional[str]:
        """
        Process client answer text.
        
        Returns the answer to store, or None if no question pending.
        """
        if not self.current_question_id:
            return None
        
        # Check if it's a number selection
        text = text.strip()
        
        # Store the answer
        write_answer(self.current_question_id, text, source="telegram")
        
        answered_id = self.current_question_id
        self.current_question_id = None
        
        return answered_id
    
    async def poll_once(self) -> bool:
        """
        Check for pending questions and deliver one if found.
        
        Returns True if a question was delivered.
        """
        # Don't deliver new questions if one is pending answer
        if self.current_question_id:
            return False
        
        pending = get_pending_questions()
        if pending:
            question = pending[0]  # Deliver one at a time
            return await self.deliver_question(question)
        
        return False
    
    async def run(self):
        """Run the polling loop"""
        self.running = True
        logger.info("Question poller started")
        
        while self.running:
            try:
                await self.poll_once()
            except Exception as e:
                logger.error(f"Poll error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the polling loop"""
        self.running = False
        logger.info("Question poller stopped")
