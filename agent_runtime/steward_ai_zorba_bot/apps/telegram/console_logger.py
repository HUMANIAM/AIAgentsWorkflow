#!/usr/bin/env python3
"""Simple console logging with emoji prefixes"""


class Log:
    """Provides formatted console output"""
    
    ICONS = {
        'info': 'ℹ️', 'ok': '✅', 'err': '❌', 'warn': '⚠️',
        'exchange': '📊', 'recv': '📥', 'send': '📤', 'go': '🚀', 'wait': '⏳'
    }
    
    @staticmethod
    def msg(text: str, icon: str = 'info'):
        """Print message with icon"""
        icon_str = Log.ICONS.get(icon, '•')
        print(f"{icon_str} {text}")
    
    @staticmethod
    def ok(text: str): Log.msg(text, 'ok')
    @staticmethod
    def err(text: str): Log.msg(text, 'err')
    @staticmethod
    def warn(text: str): Log.msg(text, 'warn')
    @staticmethod
    def exchange(text: str): Log.msg(text, 'exchange')
    @staticmethod
    def recv(text: str): Log.msg(text, 'recv')
    @staticmethod
    def send(text: str): Log.msg(text, 'send')
    @staticmethod
    def go(text: str): Log.msg(text, 'go')
    @staticmethod
    def wait(text: str): Log.msg(text, 'wait')
