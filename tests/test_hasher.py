"""Tests for secret code generator."""
import sys
sys.path.insert(0, '.')

from src.hasher import hash_int


def test_secret_code_generation():
    """AC-01: hash_int(42) returns 64-char hex string"""
    result = hash_int(42)
    assert len(result) == 64
    assert all(c in '0123456789abcdef' for c in result)


def test_deterministic_behavior():
    """AC-02: Same input always produces same output"""
    assert hash_int(123) == hash_int(123)
    assert hash_int(0) == hash_int(0)
    assert hash_int(-999) == hash_int(-999)


def test_different_inputs():
    """Different inputs should produce different outputs"""
    assert hash_int(1) != hash_int(2)
    assert hash_int(100) != hash_int(200)
