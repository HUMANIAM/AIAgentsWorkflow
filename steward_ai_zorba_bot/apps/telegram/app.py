#!/usr/bin/env python3
"""
Telegram channel implementation for steward_ai_zorba_bot
Provides the run() coroutine for the main app selector
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters

from .bot_config import Config
from .telegram_handler import send_msg, reply, get_user_id, get_text
from .console_logger import Log
from .question_poller import QuestionPoller
from .idea_chat import IdeaChat

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot implementation"""
    
    def __init__(self):
        """Initialize bot with config"""
        try:
            self.config = Config()
            self.app = None
            self.question_poller = None
            self.idea_chat = None
            Log.ok("Telegram bot initialized")
        except Exception as e:
            Log.err(f"Failed to initialize bot: {e}")
            raise
    
    async def handle_idea_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /idea commands"""
        user_id = get_user_id(update)
        text = get_text(update)
        
        if not user_id or not text:
            return
        
        if not self.config.is_allowed(user_id):
            Log.warn(f"Unauthorized user {user_id}")
            return
        
        Log.recv(f"From {user_id}: {text}")
        
        if self.idea_chat:
            await self.idea_chat.handle_command(user_id, text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        user_id = get_user_id(update)
        text = get_text(update)
        
        if not user_id or not text:
            return
        
        if not self.config.is_allowed(user_id):
            Log.warn(f"Unauthorized user {user_id}")
            return
        
        # Log incoming message
        Log.recv(f"From {user_id}: {text}")
        
        # Check if user has active idea session
        if self.idea_chat:
            from services.idea_handler import get_active_idea
            if get_active_idea(user_id):
                await self.idea_chat.process_message(user_id, text)
                return
        
        # Check if this is an answer to a pending question
        if self.question_poller and self.question_poller.current_question_id:
            answered_id = self.question_poller.process_answer(text)
            if answered_id:
                Log.ok(f"Answer received for {answered_id}: {text}")
                await reply(update, f"✅ Got it! Your answer has been recorded. The team will continue working.")
                return
        
        # Default: acknowledge message
        await reply(update, f"📨 Received: {text}\n\n_No pending questions right now. Send /idea to start brainstorming._")
    
    async def send_to_user(self, user_id: int, text: str) -> None:
        """Send message to a specific user (used by question poller)"""
        if self.app and self.app.bot:
            await send_msg(self.app.bot, user_id, text)
    
    async def run(self):
        """Run the Telegram bot"""
        Log.go("Starting Telegram bot...")
        
        try:
            # Create app
            self.app = Application.builder().token(self.config.token).build()
            
            # Add /idea command handler
            self.app.add_handler(
                CommandHandler("idea", self.handle_idea_command)
            )
            
            # Add message handler (for non-command messages)
            self.app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            # Initialize
            Log.wait("Initializing...")
            await self.app.initialize()
            await self.app.start()
            
            # Start polling
            await self.app.updater.start_polling(drop_pending_updates=True)
            Log.ok("Bot polling started")
            
            # Initialize and start question poller
            self.question_poller = QuestionPoller(
                send_func=self.send_to_user,
                user_ids=self.config.real_users()
            )
            asyncio.create_task(self.question_poller.run())
            Log.ok("Question poller started")
            
            # Initialize idea chat handler
            self.idea_chat = IdeaChat(send_func=self.send_to_user)
            Log.ok("Idea chat handler started")
            
            # Send startup message to admins
            for user_id in self.config.real_users():
                await send_msg(self.app.bot, user_id, "🤖 Telegram bot started - listening for team questions")
            
            # Keep running
            Log.wait("Waiting for messages...")
            await asyncio.Event().wait()
            
        except Exception as e:
            Log.err(f"Error: {e}")
            raise
        finally:
            try:
                if self.question_poller:
                    self.question_poller.stop()
                if self.app:
                    await self.app.updater.stop()
                    await self.app.stop()
                    await self.app.shutdown()
            except Exception:
                pass


# Global bot instance
_bot = None


async def run():
    """Entry point for app selector - initialize and run Telegram bot"""
    global _bot
    try:
        _bot = TelegramBot()
        await _bot.run()
    except Exception as e:
        logger.error(f"Telegram bot failed: {e}")
        raise
