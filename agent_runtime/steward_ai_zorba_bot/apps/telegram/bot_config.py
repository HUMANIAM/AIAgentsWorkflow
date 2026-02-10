#!/usr/bin/env python3
"""Bot configuration from environment"""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Load and manage bot configuration"""
    
    def __init__(self):
        # Find and load .env file
        env_file = Path(__file__).parent.parent.parent / ".env"
        
        if not env_file.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")
        
        load_dotenv(env_file)
        
        self.token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
        self.users = self._parse_users()
        
        self._validate()
        self.bot_id = int(self.token.split(':')[0])
    
    def _validate(self):
        """Validate configuration"""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN: required, cannot be empty")
        
        if ':' not in self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN: invalid format (expected 'id:token')")
        
        try:
            int(self.token.split(':')[0])
        except ValueError:
            raise ValueError("TELEGRAM_BOT_TOKEN: bot ID must be numeric")
        
        if not self.users:
            raise ValueError("TELEGRAM_ALLOWED_USER_IDS: required, cannot be empty")
    
    def _parse_users(self) -> list:
        """Parse comma-separated user IDs"""
        users_str = os.getenv('TELEGRAM_ALLOWED_USER_IDS', '').strip()
        if not users_str:
            return []
        
        users = []
        for u_str in users_str.split(','):
            u_str = u_str.strip()
            if not u_str:
                continue
            try:
                users.append(int(u_str))
            except ValueError:
                raise ValueError(f"TELEGRAM_ALLOWED_USER_IDS: '{u_str}' is not numeric")
        
        return users
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed"""
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        return user_id in self.users
    
    def is_bot(self, user_id: int) -> bool:
        """Check if ID is the bot itself"""
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        return user_id == self.bot_id
    
    def real_users(self) -> list:
        """Get list of human users (exclude bot)"""
        return [u for u in self.users if u != self.bot_id]
