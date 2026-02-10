#!/usr/bin/env python3
"""Telegram bot communication helpers"""

import logging
from telegram import Update, Bot

logger = logging.getLogger(__name__)


async def send_msg(bot: Bot, chat_id: int, text: str) -> bool:
    """Send message to chat
    
    Args:
        bot: Telegram bot instance
        chat_id: Target chat ID
        text: Message text
        
    Returns:
        True if sent, False on error
    """
    if not isinstance(chat_id, int) or chat_id <= 0:
        logger.error(f"Invalid chat_id: {chat_id} (must be positive integer)")
        return False
    
    if not isinstance(text, str) or not text.strip():
        logger.error(f"Invalid text: empty or not string")
        return False
    
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.error(f"Send failed to {chat_id}: {e}")
        return False


async def reply(update: Update, text: str) -> bool:
    """Reply to user message
    
    Args:
        update: Telegram update object
        text: Reply text
        
    Returns:
        True if sent, False on error
    """
    if update is None or update.message is None:
        logger.error("Invalid update object")
        return False
    
    if not isinstance(text, str) or not text.strip():
        logger.error(f"Invalid reply text: empty or not string")
        return False
    
    try:
        await update.message.reply_text(text)
        return True
    except Exception as e:
        logger.error(f"Reply failed: {e}")
        return False


def get_user_id(update: Update) -> int:
    """Extract user ID from update"""
    return update.effective_user.id if update.effective_user else 0


def get_text(update: Update) -> str:
    """Extract message text from update"""
    return update.message.text.strip() if update.message and update.message.text else ""
