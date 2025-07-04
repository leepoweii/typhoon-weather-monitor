"""
Notifications module for Typhoon Weather Monitor
Handles LINE Bot notifications with text-only messaging
"""

# FlexMessageBuilder disabled - using text-only messaging
from .line_bot import LineNotifier, create_webhook_handler

__all__ = ['LineNotifier', 'create_webhook_handler']