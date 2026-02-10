#!/usr/bin/env python3
"""Telegram Bot Integration Test - Reverse Messages"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from apps.telegram import Config, reverse_message, send_msg, reply, get_user_id, get_text, Tracker, Log


def print_header():
    """Print test header"""
    print("\n" + "=" * 70)
    print("🤖 TELEGRAM BOT - REVERSE MESSAGE TEST")
    print("=" * 70 + "\n")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_id = get_user_id(update)
    text = get_text(update)
    
    if not user_id or not text:
        return
    
    if not config.is_allowed(user_id):
        Log.warn(f"Unauthorized user {user_id}")
        return
    
    # Next exchange
    if not tracker.next():
        Log.ok("All exchanges completed!")
        return
    
    # Log and process
    Log.exchange(f"Exchange {tracker.progress()}")
    Log.recv(f"Message: '{text}'")
    
    reversed_text = reverse_message(text)
    Log.send(f"Reversed: '{reversed_text}'")
    
    # Send response
    await reply(update, f"🔄 Reversed: {reversed_text}")


async def send_startup_msg(app: Application):
    """Send startup message to users"""
    for user_id in config.real_users():
        msg = "👋 Hello! I'm the Reverse Message Bot.\nSend any message and I'll reverse it. Let's do 6 exchanges! 🔄"
        await send_msg(app.bot, user_id, msg)
        Log.send(f"Startup message sent to user {user_id}")


async def main():
    """Main entry point"""
    print_header()
    
    try:
        # Create app
        app = Application.builder().token(config.token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        Log.go("Initializing bot...")
        await app.initialize()
        await app.start()
        
        # Start polling
        await app.updater.start_polling(drop_pending_updates=True)
        Log.go("Bot polling active")
        
        # Send startup message
        await send_startup_msg(app)
        Log.wait("Waiting for messages...")
        
        # Run until done
        while not tracker.done():
            await asyncio.sleep(10)
        
        Log.ok(f"Test complete! {tracker.progress()} exchanges")
        return 0
        
    except (asyncio.CancelledError, KeyboardInterrupt):
        Log.warn("Test cancelled")
        return 1
    except Exception as e:
        Log.err(f"Error: {e}")
        return 1
    finally:
        try:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    config = Config()
    tracker = Tracker(max_exchanges=6)
    exit(asyncio.run(main()))
