#!/usr/bin/env python3
"""Unit tests for validation and error handling"""

import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram import Config, reverse_message, Tracker


class TestConfigValidation(unittest.TestCase):
    """Test bot_config validation"""
    
    def test_missing_env_file(self):
        """Test missing .env file raises error"""
        # Note: This would require actual missing .env file or better mocking
        # Skip for now since .env exists in the project
        pass
    
    def test_missing_token(self):
        """Test missing TELEGRAM_BOT_TOKEN"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '', 'TELEGRAM_ALLOWED_USER_IDS': '123'}):
            with self.assertRaises(ValueError) as ctx:
                Config()
            self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))
    
    def test_invalid_token_format(self):
        """Test invalid token format (missing colon)"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'invalid_token', 'TELEGRAM_ALLOWED_USER_IDS': '123'}):
            with self.assertRaises(ValueError) as ctx:
                Config()
            self.assertIn("invalid format", str(ctx.exception))
    
    def test_non_numeric_bot_id(self):
        """Test non-numeric bot ID in token"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'abc:token123', 'TELEGRAM_ALLOWED_USER_IDS': '123'}):
            with self.assertRaises(ValueError) as ctx:
                Config()
            self.assertIn("numeric", str(ctx.exception))
    
    def test_missing_users(self):
        """Test missing TELEGRAM_ALLOWED_USER_IDS"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '123:token', 'TELEGRAM_ALLOWED_USER_IDS': ''}):
            with self.assertRaises(ValueError) as ctx:
                Config()
            self.assertIn("TELEGRAM_ALLOWED_USER_IDS", str(ctx.exception))
    
    def test_non_numeric_user_id(self):
        """Test non-numeric user ID"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '123:token', 'TELEGRAM_ALLOWED_USER_IDS': 'abc,123'}):
            with self.assertRaises(ValueError) as ctx:
                Config()
            self.assertIn("not numeric", str(ctx.exception))
    
    def test_is_allowed_invalid_type(self):
        """Test is_allowed with invalid type"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '123:token', 'TELEGRAM_ALLOWED_USER_IDS': '456'}):
            config = Config()
            self.assertFalse(config.is_allowed("456"))  # String, not int
            self.assertFalse(config.is_allowed(-1))     # Negative
            self.assertFalse(config.is_allowed(0))      # Zero
    
    def test_is_bot_invalid_type(self):
        """Test is_bot with invalid type"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '123:token', 'TELEGRAM_ALLOWED_USER_IDS': '456'}):
            config = Config()
            self.assertFalse(config.is_bot("123"))  # String, not int
            self.assertFalse(config.is_bot(-1))     # Negative


class TestMessageValidation(unittest.TestCase):
    """Test message_processor validation"""
    
    def test_reverse_none(self):
        """Test reversing None"""
        with self.assertRaises(ValueError) as ctx:
            reverse_message(None)
        self.assertIn("None", str(ctx.exception))
    
    def test_reverse_not_string(self):
        """Test reversing non-string"""
        with self.assertRaises(ValueError) as ctx:
            reverse_message(123)
        self.assertIn("string", str(ctx.exception))
    
    def test_reverse_empty_string(self):
        """Test reversing empty string"""
        with self.assertRaises(ValueError) as ctx:
            reverse_message("")
        self.assertIn("empty", str(ctx.exception))
    
    def test_reverse_whitespace_only(self):
        """Test reversing whitespace-only string"""
        with self.assertRaises(ValueError) as ctx:
            reverse_message("   ")
        self.assertIn("empty", str(ctx.exception))
    
    def test_reverse_valid(self):
        """Test reversing valid string"""
        result = reverse_message("hello")
        self.assertEqual(result, "olleh")
    
    def test_reverse_with_spaces(self):
        """Test reversing string with spaces"""
        result = reverse_message("hello world")
        self.assertEqual(result, "dlrow olleh")
    
    def test_reverse_special_chars(self):
        """Test reversing with special chars"""
        result = reverse_message("test@123")
        self.assertEqual(result, "321@tset")


class TestTrackerValidation(unittest.TestCase):
    """Test conversation_tracker validation"""
    
    def test_invalid_max_exchanges_zero(self):
        """Test max_exchanges must be positive"""
        with self.assertRaises(ValueError) as ctx:
            Tracker(max_exchanges=0)
        self.assertIn("positive", str(ctx.exception))
    
    def test_invalid_max_exchanges_negative(self):
        """Test max_exchanges cannot be negative"""
        with self.assertRaises(ValueError) as ctx:
            Tracker(max_exchanges=-5)
        self.assertIn("positive", str(ctx.exception))
    
    def test_invalid_max_exchanges_type(self):
        """Test max_exchanges must be int"""
        with self.assertRaises(ValueError) as ctx:
            Tracker(max_exchanges="5")
        self.assertIn("integer", str(ctx.exception))
    
    def test_tracker_next(self):
        """Test tracker.next()"""
        tracker = Tracker(max_exchanges=2)
        self.assertTrue(tracker.next())   # 1
        self.assertTrue(tracker.next())   # 2
        self.assertFalse(tracker.next())  # Over limit
    
    def test_tracker_done(self):
        """Test tracker.done()"""
        tracker = Tracker(max_exchanges=2)
        self.assertFalse(tracker.done())
        tracker.next()
        self.assertFalse(tracker.done())
        tracker.next()
        self.assertTrue(tracker.done())
    
    def test_tracker_progress(self):
        """Test tracker.progress()"""
        tracker = Tracker(max_exchanges=3)
        self.assertEqual(tracker.progress(), "0/3")
        tracker.next()
        self.assertEqual(tracker.progress(), "1/3")
        tracker.next()
        self.assertEqual(tracker.progress(), "2/3")
        tracker.next()
        self.assertEqual(tracker.progress(), "3/3")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in edge cases"""
    
    def test_config_whitespace_handling(self):
        """Test config handles whitespace correctly"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '  123:token  ',
            'TELEGRAM_ALLOWED_USER_IDS': '  456 , 789  '
        }):
            config = Config()
            self.assertEqual(config.token, '123:token')
            self.assertIn(456, config.users)
            self.assertIn(789, config.users)
    
    def test_message_whitespace_stripping(self):
        """Test message whitespace is stripped before reversing"""
        result = reverse_message("  hello  ")
        self.assertEqual(result, "olleh")  # Both leading and trailing stripped
    
    def test_tracker_count_boundary(self):
        """Test tracker at boundary"""
        tracker = Tracker(max_exchanges=1)
        self.assertTrue(tracker.next())   # count=1
        self.assertFalse(tracker.next())  # Over limit
        self.assertTrue(tracker.done())


if __name__ == '__main__':
    unittest.main()
