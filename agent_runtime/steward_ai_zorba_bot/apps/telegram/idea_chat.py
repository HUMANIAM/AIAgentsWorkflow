#!/usr/bin/env python3
"""Idea chat handler - manages /idea command interactions."""

from __future__ import annotations

import logging
import re
from typing import Awaitable, Callable, Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.idea_handler import (
    STATE_ACTIVATED,
    STATE_DONE,
    STATE_EXECUTING,
    STATE_NEW,
    STATE_PLANNED,
    STATE_REFINED,
    STATE_REFINING,
    STATE_WAITING_REALIZATION_APPROVAL,
    VALID_STATES,
    activate_idea,
    add_message,
    append_runtime_adjustments,
    complete_idea,
    create_idea,
    end_idea,
    execute_idea,
    get_active_idea,
    get_active_sessions,
    get_chat_history,
    get_last_gpt_message,
    idea_exists,
    list_ideas,
    list_ideas_by_state,
    normalize_idea_id,
    plan_idea,
    restore_active_sessions,
    start_idea,
)
from services.openai_client import chat_about_idea, generate_context_from_chat, propose_idea_bootstrap

logger = logging.getLogger(__name__)


def _normalize_command_text(text: str) -> str:
    """Normalize /idea command text for robust parsing."""
    command = (text or "").strip()
    command = re.sub(r"^/idea@[A-Za-z0-9_]+", "/idea", command, flags=re.IGNORECASE)
    command = re.sub(r"\s+", " ", command)
    return command


class IdeaChat:
    """Manages idea brainstorming sessions."""

    def __init__(self, send_func: Callable[[int, str], Awaitable[None]]):
        self.send_func = send_func
        restore_active_sessions()

    async def send_resume_messages(self) -> None:
        """Notify users about recovered refining sessions on startup."""
        sessions = get_active_sessions()
        for user_id, idea_id in sessions.items():
            last_gpt = get_last_gpt_message(idea_id)
            if last_gpt:
                if len(last_gpt) > 1300:
                    last_gpt = last_gpt[:1300] + "..."
                msg = (
                    "🔁 *Recovered your refining idea session*\n"
                    f"📝 ID: `{idea_id}`\n\n"
                    f"🤖 *Last GPT message:*\n{last_gpt}\n\n"
                    "_Send your next message to continue, or `/idea stop` to close this session._"
                )
            else:
                msg = (
                    "🔁 *Recovered your refining idea session*\n"
                    f"📝 ID: `{idea_id}`\n\n"
                    "_Send your next message to continue, or `/idea stop` to close this session._"
                )
            await self.send_func(user_id, msg)
            logger.info("Recovery message sent for idea %s to user %s", idea_id, user_id)

    async def handle_command(self, user_id: int, text: str) -> bool:
        """Handle /idea commands."""
        text = _normalize_command_text(text)

        if text == "/idea stop":
            await self.stop_session(user_id)
            return True

        if text.startswith("/idea list"):
            parts = text.split()
            state = parts[2] if len(parts) > 2 else None
            await self.list_by_state(user_id, state)
            return True

        if text.startswith("/idea plan "):
            idea_id = normalize_idea_id(text.replace("/idea plan ", "", 1).strip())
            await self.plan(user_id, idea_id)
            return True

        if text.startswith("/idea activate "):
            idea_id = normalize_idea_id(text.replace("/idea activate ", "", 1).strip())
            await self.activate(user_id, idea_id)
            return True

        if text.startswith("/idea active "):
            idea_id = normalize_idea_id(text.replace("/idea active ", "", 1).strip())
            await self.activate(user_id, idea_id)
            return True

        if text.startswith("/idea execute "):
            idea_id = normalize_idea_id(text.replace("/idea execute ", "", 1).strip())
            await self.execute(user_id, idea_id)
            return True

        if text.startswith("/idea done "):
            idea_id = normalize_idea_id(text.replace("/idea done ", "", 1).strip())
            await self.done(user_id, idea_id)
            return True

        if text.startswith("/idea start "):
            idea_id = normalize_idea_id(text.replace("/idea start ", "", 1).strip())
            await self.start_existing_session(user_id, idea_id)
            return True

        if text.startswith("/idea continue "):
            idea_id = normalize_idea_id(text.replace("/idea continue ", "", 1).strip())
            await self.start_existing_session(user_id, idea_id)
            return True

        if text == "/idea":
            await self.start_session(user_id)
            return True

        if text.startswith("/idea "):
            arg = text.replace("/idea ", "", 1).strip()
            await self.start_or_resume_from_argument(user_id, arg)
            return True

        return False

    async def start_session(self, user_id: int) -> None:
        """Handle bare /idea."""
        active = get_active_idea(user_id)
        if active:
            await self.send_func(
                user_id,
                "💡 You already have an active refining session.\n\n"
                "Continue chatting, or send `/idea stop` to close it.",
            )
            return

        await self.send_func(
            user_id,
            "💡 *New idea flow ready*\n\n"
            "What do you have in mind? Send `/idea <headline>` to start a refining session.",
        )

    async def start_or_resume_from_argument(self, user_id: int, arg: str) -> None:
        """Handle /idea <headline-or-id>."""
        if not arg:
            await self.start_session(user_id)
            return

        candidate_id = normalize_idea_id(arg)
        if candidate_id and idea_exists(candidate_id):
            await self.start_existing_session(user_id, candidate_id)
            return

        await self.start_with_headline(user_id, arg)

    async def start_existing_session(self, user_id: int, idea_id: str) -> None:
        """Resume an existing idea by ID -> REFINING."""
        if not idea_id:
            await self.send_func(user_id, "❌ Missing idea ID. Usage: `/idea start <id>`")
            return

        active = get_active_idea(user_id)
        if active and active != idea_id:
            await self.send_func(
                user_id,
                f"❌ You already have an active refining session (`{active}`).\n\n"
                "Send `/idea stop` first, then start another idea.",
            )
            return

        success, message = start_idea(user_id, idea_id)
        if not success:
            await self.send_func(user_id, f"❌ {message}")
            return

        last_gpt = get_last_gpt_message(idea_id)
        if last_gpt:
            await self.send_func(
                user_id,
                "✅ *Refining session resumed*\n"
                f"📝 ID: `{idea_id}`\n"
                f"📊 Status: `{STATE_REFINING}`\n\n"
                f"🤖 *Last GPT message:*\n{last_gpt}\n\n"
                "_Send your next message, or `/idea stop` to close._",
            )
        else:
            await self.send_func(
                user_id,
                "✅ *Refining session resumed*\n"
                f"📝 ID: `{idea_id}`\n"
                f"📊 Status: `{STATE_REFINING}`\n\n"
                "_Send your next message, or `/idea stop` to close._",
            )

    async def start_with_headline(self, user_id: int, seed_headline: str) -> None:
        """Create a new idea file by GPT-refined headline/id and begin REFINING."""
        active = get_active_idea(user_id)
        if active:
            await self.send_func(
                user_id,
                f"❌ You already have an active refining session (`{active}`).\n\n"
                "Send `/idea stop` before starting a new one.",
            )
            return

        await self.send_func(user_id, "⏳ Creating idea file with GPT-refined headline...")

        runtime_adjustments = []
        conflict_note = ""

        for _attempt in range(3):
            proposal = propose_idea_bootstrap(seed_headline, conflict_note=conflict_note)
            headline = proposal.get("headline", "").strip() or seed_headline.strip() or "Untitled Idea"
            idea_id = normalize_idea_id(proposal.get("idea_id", "")) or normalize_idea_id(headline)
            assistant_message = proposal.get("assistant_message", "").strip()

            if not idea_id:
                conflict_note = "The proposed idea_id was invalid. Propose a different lowercase snake_case id."
                runtime_adjustments.append(f"GPT proposal invalid for seed `{seed_headline}`. Requested a new unique id.")
                continue

            if idea_exists(idea_id):
                conflict_note = (
                    f"Conflict: idea_id `{idea_id}` already exists. "
                    "Propose a different unique lowercase snake_case id."
                )
                runtime_adjustments.append(
                    f"Conflict detected for candidate id `{idea_id}`. Sent conflict note back to GPT for runtime adjustment."
                )
                runtime_adjustments.append(
                    f"GPT conflict proposal: headline=`{headline}`, idea_id=`{idea_id}`"
                )
                continue

            ok, created = create_idea(user_id, idea_id, headline, initial_status=STATE_REFINING)
            if not ok:
                conflict_note = (
                    f"Conflict or creation issue for idea_id `{idea_id}`: {created}. "
                    "Propose a different unique lowercase snake_case id."
                )
                runtime_adjustments.append(
                    f"Create attempt failed for id `{idea_id}` with error `{created}`. Requested new id from GPT."
                )
                continue

            if runtime_adjustments:
                append_runtime_adjustments(created, runtime_adjustments)

            add_message(created, "user", seed_headline)
            add_message(created, "gpt", assistant_message)

            await self.send_func(
                user_id,
                "✅ *Idea session started*\n\n"
                f"💡 *Headline:* {headline}\n"
                f"📝 *ID:* `{created}`\n"
                f"📊 *Status:* `{STATE_REFINING}`\n\n"
                f"🤖 {assistant_message}\n\n"
                "_Send your next message to continue, or `/idea stop` to close this session._",
            )
            logger.info("Started refining idea %s for user %s", created, user_id)
            return

        await self.send_func(
            user_id,
            "❌ GPT could not generate a unique idea id after 3 retries.\n\n"
            "Please send a different `/idea <headline>` and I will retry.",
        )

    async def process_message(self, user_id: int, text: str) -> bool:
        """Process free text in an active REFINING session."""
        idea_id = get_active_idea(user_id)
        if not idea_id:
            return False

        add_message(idea_id, "user", text)
        history = get_chat_history(idea_id)

        # `chat_about_idea` appends `new_message`, so pass prior history snapshot.
        prior_history = history[:-1] if history and history[-1].get("role") == "user" else history
        try:
            gpt_response = chat_about_idea(prior_history, text)
        except Exception as exc:
            logger.exception("GPT brainstorming response failed for idea %s: %s", idea_id, exc)
            gpt_response = (
                "I saved your message, but I hit a temporary issue generating the next response. "
                "Please send the same message again."
            )

        add_message(idea_id, "gpt", gpt_response)
        await self.send_func(user_id, f"🤖 {gpt_response}")

        logger.info("Idea %s: user message processed", idea_id)
        return True

    async def stop_session(self, user_id: int) -> None:
        """Close active idea refinement -> REFINED."""
        idea_id = get_active_idea(user_id)
        if not idea_id:
            await self.send_func(user_id, "❌ No active idea session. Send `/idea <headline>` to start one.")
            return

        history = get_chat_history(idea_id)
        if not history:
            end_idea(user_id)
            await self.send_func(user_id, "❌ No conversation recorded. Session closed.")
            return

        ended = end_idea(user_id)
        await self.send_func(
            user_id,
            "✅ *Idea session closed*\n\n"
            f"📝 ID: `{ended}`\n"
            f"📊 Status: `{STATE_REFINED}`\n\n"
            "Thanks for the brainstorming session. Have a good day.",
        )

    async def list_by_state(self, user_id: int, state: Optional[str] = None) -> None:
        """List idea files for this owner, optionally filtered by state."""
        status_emojis = {
            STATE_NEW: "💡",
            STATE_REFINING: "🔄",
            STATE_REFINED: "🧠",
            STATE_PLANNED: "📋",
            STATE_ACTIVATED: "🟢",
            STATE_EXECUTING: "🚀",
            STATE_WAITING_REALIZATION_APPROVAL: "⏸️",
            STATE_DONE: "✅",
        }

        if state:
            state_upper = state.upper()
            if state_upper not in VALID_STATES:
                valid = "`, `".join(s.lower() for s in VALID_STATES)
                await self.send_func(user_id, f"❌ Invalid state: `{state}`\n\nValid states: `{valid}`")
                return
            ideas = list_ideas_by_state(state_upper, owner_user_id=user_id)
            title = f"📋 *Ideas ({state_upper}):*"
        else:
            ideas = list_ideas(owner_user_id=user_id)
            title = "📋 *All Ideas:*"

        if not ideas:
            await self.send_func(user_id, f"{title}\n\n_No ideas found. Send `/idea <headline>` to start brainstorming._")
            return

        msg = f"{title}\n\n"
        for i, idea in enumerate(ideas, 1):
            emoji = status_emojis.get(idea.get("status", ""), "❓")
            msg += (
                f"{i}. {emoji} `{idea.get('id')}`\n"
                f"   {idea.get('headline')} ({idea.get('status')})\n\n"
            )

        msg += "*Commands:*\n"
        msg += "• `/idea start <id>` - Resume refining\n"
        msg += "• `/idea plan <id>` - Generate PM/BA context\n"
        msg += "• `/idea activate <id>` - Copy `context_<id>.md` to active `context.md`\n"
        msg += "• `/idea execute <id>` - Trigger orchestrator\n"
        msg += "• `/idea done <id>` - Mark done after realization approval"

        await self.send_func(user_id, msg)

    async def plan(self, user_id: int, idea_id: str) -> None:
        """Generate `context_<id>.md` and set status -> PLANNED."""
        if not idea_id:
            await self.send_func(user_id, "❌ Please provide an idea ID. Usage: `/idea plan <id>`")
            return

        history = get_chat_history(idea_id)
        if not history:
            await self.send_func(user_id, f"❌ No chat history found for idea: `{idea_id}`")
            return

        await self.send_func(user_id, "⏳ Generating PM/BA context from idea history...")
        try:
            context_content = generate_context_from_chat(history, idea_id=idea_id)
        except Exception as exc:
            await self.send_func(
                user_id,
                f"❌ Context generation failed: {exc}",
            )
            return

        success, message = plan_idea(idea_id, context_content, owner_user_id=user_id)

        if success:
            await self.send_func(
                user_id,
                f"✅ *{message}*\n\n"
                f"📄 `plugin/context_{idea_id}.md` created\n"
                f"📊 *Status:* `{STATE_PLANNED}`\n\n"
                f"*Next step:* `/idea activate {idea_id}`",
            )
        else:
            await self.send_func(user_id, f"❌ {message}")

        logger.info("Plan requested for idea %s by user %s", idea_id, user_id)

    async def activate(self, user_id: int, idea_id: str) -> None:
        """Activate idea context into plugin/context.md."""
        if not idea_id:
            await self.send_func(user_id, "❌ Please provide an idea ID. Usage: `/idea activate <id>`")
            return

        success, message = activate_idea(idea_id, owner_user_id=user_id)
        if success:
            await self.send_func(
                user_id,
                f"✅ *{message}*\n\n"
                f"📄 `plugin/context_{idea_id}.md` copied to active `plugin/context.md`.\n\n"
                f"📊 *Status:* `{STATE_ACTIVATED}`\n\n"
                f"*Next step:* `/idea execute {idea_id}`",
            )
        else:
            await self.send_func(user_id, f"❌ {message}")

        logger.info("Activate requested for idea %s by user %s", idea_id, user_id)

    async def execute(self, user_id: int, idea_id: str) -> None:
        """Trigger orchestrator execution for planned/activated idea."""
        if not idea_id:
            await self.send_func(user_id, "❌ Please provide an idea ID. Usage: `/idea execute <id>`")
            return

        await self.send_func(user_id, "⏳ Triggering orchestrator for active idea...")
        success, message = execute_idea(idea_id, owner_user_id=user_id)
        if success:
            await self.send_func(
                user_id,
                f"🚀 *Execution triggered for `{idea_id}`*\n\n"
                f"{message}\n\n"
                "_The orchestrator is running autonomously and will pause only at required human gates._",
            )
        else:
            await self.send_func(user_id, f"❌ {message}")

        logger.info("Execute requested for idea %s by user %s", idea_id, user_id)

    async def done(self, user_id: int, idea_id: str) -> None:
        """Mark an idea done after realization approval gate."""
        if not idea_id:
            await self.send_func(user_id, "❌ Please provide an idea ID. Usage: `/idea done <id>`")
            return

        success, message = complete_idea(idea_id, owner_user_id=user_id)
        if success:
            await self.send_func(
                user_id,
                f"🎉 *{message}*\n\n"
                f"📊 *Status:* `{STATE_DONE}`\n\n"
                "Great work. Use `/idea list done` to see completed ideas.",
            )
        else:
            await self.send_func(user_id, f"❌ {message}")

        logger.info("Done requested for idea %s by user %s", idea_id, user_id)
