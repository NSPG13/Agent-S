"""
Agent-S3 Browser Module

Provides browser automation via Chrome extension with WebSocket bridge.
"""

from .bridge import BrowserBridge, get_browser_bridge

__all__ = ["BrowserBridge", "get_browser_bridge"]
