#!/usr/bin/env python3
"""Unit Tests for Telegram Channel Modules"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram import reverse_message, Tracker, Log


class TestMessageProcessor(unittest.TestCase):
    """Test message processing"""
    
    def test_reverse_simple(self):
        self.assertEqual(reverse_message("hello"), "olleh")
    
    def test_reverse_empty(self):
        # Empty strings should raise ValueError (validation)
        with self.assertRaises(ValueError):
            reverse_message("")
    
    def test_reverse_special_chars(self):
        self.assertEqual(reverse_message("hello@123"), "321@olleh")


class TestTracker(unittest.TestCase):
    """Test conversation tracking"""
    
    def setUp(self):
        self.tracker = Tracker(max_exchanges=3)
    
    def test_initial_state(self):
        self.assertEqual(self.tracker.count, 0)
        self.assertFalse(self.tracker.done())
    
    def test_next_exchange(self):
        result = self.tracker.next()
        self.assertTrue(result)
        self.assertEqual(self.tracker.count, 1)
    
    def test_exchange_limit(self):
        for _ in range(3):
            self.assertTrue(self.tracker.next())
        self.assertFalse(self.tracker.next())
    
    def test_progress(self):
        self.tracker.next()
        self.tracker.next()
        self.assertEqual(self.tracker.progress(), "2/3")
    
    def test_completion(self):
        for _ in range(3):
            self.tracker.next()
        self.assertTrue(self.tracker.done())


class TestLog(unittest.TestCase):
    """Test logger"""
    
    def test_icons_exist(self):
        self.assertIn('ok', Log.ICONS)
        self.assertIn('err', Log.ICONS)
        self.assertIn('exchange', Log.ICONS)


if __name__ == '__main__':
    unittest.main()
