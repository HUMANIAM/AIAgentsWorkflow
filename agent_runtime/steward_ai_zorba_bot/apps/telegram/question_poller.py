#!/usr/bin/env python3
"""Question poller - polls status.json and delivers questions to client via Telegram"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable, Awaitable

import sys
from pathlib import Path
# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.status_handler import (
    get_pending_questions,
    get_delivered_questions,
    handle_gate_answer,
    mark_question_delivered,
    read_status,
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
        self.last_feedback: str = ""
        self.last_needs_clarification: bool = False
        self.notified_completed_runs: set[str] = set()

    def _resolve_active_question_id(self) -> Optional[str]:
        """Resolve active question id from memory, or recover from delivered state."""
        if self.current_question_id:
            return self.current_question_id

        delivered = get_delivered_questions()
        if not delivered:
            return None

        recovered_id = delivered[0].get("id")
        if recovered_id:
            self.current_question_id = recovered_id
            logger.info(f"Recovered delivered question context: {recovered_id}")
            return recovered_id

        return None

    def has_open_question(self) -> bool:
        """Whether at least one delivered question is awaiting client answer."""
        return self._resolve_active_question_id() is not None

    def _is_gate_question(self, question: dict) -> bool:
        kind = str(question.get("kind", "")).strip().lower()
        if kind == "governance_gate":
            return True
        if str(question.get("gate_id", "")).strip():
            return True
        return str(question.get("id", "")).upper().startswith("Q-GATE-")

    def _completion_run_key(self, status: Dict[str, Any]) -> str:
        run_id = str(status.get("active_run_id", "")).strip()
        if run_id:
            return run_id
        idea_id = str(status.get("active_idea_id", "")).strip()
        started = str(status.get("timestamps", {}).get("workflow_started_at", "")).strip()
        return f"{idea_id}:{started}"

    async def _maybe_send_completion_notification(self) -> bool:
        status = read_status()
        current_phase = str(status.get("current_phase", "")).lower()
        realization_status = str(status.get("realization_status", "")).lower()
        if current_phase != "done" or realization_status != "completed":
            return False

        run_key = self._completion_run_key(status)
        if not run_key or run_key in self.notified_completed_runs:
            return False

        idea_id = str(status.get("active_idea_id", "")).strip() or "unknown_idea"
        headline = str(status.get("active_idea_headline", "")).strip()
        artifacts = status.get("artifacts", {})
        artifact_count = len(artifacts) if isinstance(artifacts, dict) else 0
        summary = (
            f"✅ *Workflow completed*\n\n"
            f"Idea: `{idea_id}`\n"
            f"Headline: {headline or '(not set)'}\n"
            f"Artifacts generated: `{artifact_count}`\n"
            f"State: `done / completed`"
        )

        for user_id in self.user_ids:
            try:
                await self.send_func(user_id, summary)
            except Exception as exc:
                logger.error(f"Failed to send completion message to {user_id}: {exc}")
                return False

        self.notified_completed_runs.add(run_key)
        return True
    
    def format_question_message(self, question: dict, suggestions: list) -> str:
        """Format question with suggestions for Telegram"""
        agent = question.get('from_agent', 'the team')
        q_text = question.get('question', question.get('text', ''))
        context = question.get('context', '')

        if self._is_gate_question(question):
            msg = f"⛔ *Approval required from {agent}:*\n\n{q_text}\n"
            if context:
                msg += f"\n_Context: {context}_\n"
            msg += (
                "\n✅ Reply with `approve` / `yes` / `1`\n"
                "❌ Reply with `reject` / `no` / `2`\n\n"
                "_Any other reply will ask for clarification._"
            )
            return msg
        
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
        
        # Get GPT suggestions for normal questions; use strict options for gate questions.
        if self._is_gate_question(question):
            suggestions = ["approve", "reject"]
        else:
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
        question_id = self._resolve_active_question_id()
        if not question_id:
            return None
        
        self.last_feedback = ""
        self.last_needs_clarification = False

        # Check if it's a number selection
        text = text.strip()

        if question_id.upper().startswith("Q-GATE-"):
            gate_result: Dict[str, Any] = handle_gate_answer(question_id, text, source="telegram")
            if gate_result.get("handled"):
                self.last_feedback = str(gate_result.get("message", "")).strip()
                if not gate_result.get("accepted", False):
                    self.last_needs_clarification = True
                    return None
                answered_id = question_id
                self.current_question_id = None
                return answered_id

        # Store generic question answer
        write_answer(question_id, text, source="telegram")
        
        answered_id = question_id
        self.current_question_id = None
        
        return answered_id
    
    async def poll_once(self) -> bool:
        """
        Check for pending questions and deliver one if found.
        
        Returns True if a question was delivered.
        """
        # Don't deliver new questions if one is pending answer.
        if self._resolve_active_question_id():
            return False
        
        pending = get_pending_questions()
        if pending:
            question = pending[0]  # Deliver one at a time
            return await self.deliver_question(question)

        return await self._maybe_send_completion_notification()
    
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
