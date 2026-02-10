#!/usr/bin/env python3
"""
steward_ai_zorba_bot - Multi-channel chat bridge
Selects chat channel based on CHAT_CHANNEL environment variable
Supports: telegram, whatsapp, slack, discord (extensible)
"""

import asyncio
import importlib
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
SUPPORTED_CHANNELS = ("telegram", "whatsapp", "slack", "discord")


def get_chat_channel() -> str:
    """Get chat channel from environment or use default"""
    channel = os.getenv('CHAT_CHANNEL', 'telegram').lower().strip()

    if channel not in SUPPORTED_CHANNELS:
        supported = ", ".join(SUPPORTED_CHANNELS)
        raise ValueError(f"Invalid CHAT_CHANNEL '{channel}'. Supported: {supported}")

    return channel


def load_channel_app(channel: str):
    """Dynamically load the app for the specified channel"""
    try:
        module_name = f'apps.{channel}'
        module = importlib.import_module(module_name)

        if not hasattr(module, 'run'):
            raise AttributeError(f"Channel '{channel}' module missing 'run' function")

        logger.info(f"✅ Loaded channel: {channel}")
        return module.run

    except ImportError as e:
        raise ImportError(
            f"Failed to load channel '{channel}': {e}. "
            f"Make sure 'apps/{channel}/' exists and exposes run()."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Error loading channel '{channel}': {e}") from e


async def main():
    """Entry point - select and run the appropriate channel"""
    logger.info("🤖 Steward AI Zorba Bot - Multi-Channel Bridge")
    logger.info("=" * 50)
    
    # Get configured channel
    channel = get_chat_channel()
    logger.info(f"📢 Using chat channel: {channel}")
    
    # Load the channel's run function
    run_func = load_channel_app(channel)
    
    # Run the channel
    try:
        await run_func()
    except KeyboardInterrupt:
        logger.info("⏹️  Shutting down...")
    except Exception as e:
        logger.error(f"❌ Error running channel: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
