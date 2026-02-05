#!/usr/bin/env python3
"""
steward_ai_zorba_bot - Multi-channel chat bridge
Selects chat channel based on CHAT_CHANNEL environment variable
Supports: telegram, whatsapp, slack, discord (extensible)
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_chat_channel() -> str:
    """Get chat channel from environment or use default"""
    channel = os.getenv('CHAT_CHANNEL', 'telegram').lower().strip()
    
    # Validate channel
    supported = ['telegram', 'whatsapp', 'slack', 'discord']
    if channel not in supported:
        logger.error(f"❌ Invalid CHAT_CHANNEL: '{channel}'. Supported: {', '.join(supported)}")
        sys.exit(1)
    
    return channel


def load_channel_app(channel: str):
    """Dynamically load the app for the specified channel"""
    try:
        # Try to import from apps.{channel}
        module_name = f'apps.{channel}'
        module = __import__(module_name, fromlist=['run'])
        
        if not hasattr(module, 'run'):
            logger.error(f"❌ Channel '{channel}' module missing 'run' function")
            sys.exit(1)
        
        logger.info(f"✅ Loaded channel: {channel}")
        return module.run
        
    except ImportError as e:
        logger.error(f"❌ Failed to load channel '{channel}': {e}")
        logger.error(f"   Make sure 'apps/{channel}/' directory exists with proper implementation")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error loading channel '{channel}': {e}")
        sys.exit(1)


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
