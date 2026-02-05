#!/usr/bin/env python3
"""
Telegram channel implementation for steward_ai_zorba_bot
Provides the run() coroutine for the main app selector
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from .bot_config import Config
from .telegram_handler import send_msg, reply, get_user_id, get_text
from .console_logger import Log

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot implementation"""
    
    def __init__(self):
        """Initialize bot with config"""
        try:
            self.config = Config()
            self.app = None
            Log.ok("Telegram bot initialized")
        except Exception as e:
            Log.err(f"Failed to initialize bot: {e}")
            raise
    
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
        
        # Echo back (default behavior)
        await reply(update, f"📨 You said: {text}")
    
    async def run(self):
        """Run the Telegram bot"""
        Log.go("Starting Telegram bot...")
        
        try:
            # Create app
            self.app = Application.builder().token(self.config.token).build()
            
            # Add message handler
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
            
            # Send startup message to admins
            for user_id in self.config.real_users():
                await send_msg(self.app.bot, user_id, "🤖 Telegram bot started")
            
            # Keep running
            Log.wait("Waiting for messages...")
            await asyncio.Event().wait()
            
        except Exception as e:
            Log.err(f"Error: {e}")
            raise
        finally:
            try:
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
