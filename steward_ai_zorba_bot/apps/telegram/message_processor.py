#!/usr/bin/env python3
"""Message processing utilities"""


def reverse_message(text: str) -> str:
    """Reverse a message text
    
    Args:
        text: Message to reverse
        
    Returns:
        Reversed message
        
    Raises:
        ValueError: If text is None, not a string, or empty
    """
    if text is None:
        raise ValueError("Message cannot be None")
    
    if not isinstance(text, str):
        raise ValueError(f"Message must be string, got {type(text).__name__}")
    
    text = text.strip()
    if not text:
        raise ValueError("Message cannot be empty")
    
    return text[::-1]
