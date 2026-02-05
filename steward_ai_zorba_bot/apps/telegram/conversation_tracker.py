#!/usr/bin/env python3
"""Conversation state tracking"""


class Tracker:
    """Track conversation exchanges"""
    
    def __init__(self, max_exchanges: int = 6):
        """Initialize tracker
        
        Args:
            max_exchanges: Maximum number of exchanges allowed
            
        Raises:
            ValueError: If max_exchanges is invalid
        """
        if not isinstance(max_exchanges, int) or max_exchanges <= 0:
            raise ValueError(f"max_exchanges must be positive integer, got {max_exchanges}")
        
        self.max_exchanges = max_exchanges
        self.count = 0
    
    def next(self) -> bool:
        """Start next exchange, return True if under limit"""
        if self.count >= self.max_exchanges:
            return False
        self.count += 1
        return True
    
    def done(self) -> bool:
        """Check if all exchanges completed"""
        return self.count >= self.max_exchanges
    
    def progress(self) -> str:
        """Get progress string"""
        return f"{self.count}/{self.max_exchanges}"
